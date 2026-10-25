"""Tests run fully offline with the mock LLM (no API key needed).

    cd backend && python -m pytest -q        (or: python -m unittest discover tests)
"""
import os
import unittest
from datetime import date

os.environ["FORMSAATHI_MOCK_LLM"] = "1"
import tempfile  # noqa: E402

os.environ["METRICS_FILE"] = os.path.join(tempfile.mkdtemp(), "sessions.jsonl")

from app import validators as V  # noqa: E402
from app.agents.vision import schema_from_vision_json  # noqa: E402
from app.forms import engine  # noqa: E402
from app.rag.retriever import retrieve  # noqa: E402
from app.service import SessionManager  # noqa: E402


def valid_aadhaar() -> str:
    prefix = "23456789012"
    return next(prefix + str(d) for d in range(10) if V.verhoeff_ok(prefix + str(d)))


def valid_gstin() -> str:
    first14 = "33ABCDE1234F1Z"
    return first14 + V.gstin_checksum(first14)


class ValidatorTests(unittest.TestCase):
    def test_aadhaar(self):
        ok, val, _ = V.validate({"type": "aadhaar"}, valid_aadhaar())
        self.assertTrue(ok)
        self.assertEqual(len(val), 14)  # spaced 4-4-4
        bad = valid_aadhaar()[:-1] + str((int(valid_aadhaar()[-1]) + 1) % 10)
        self.assertEqual(V.validate({"type": "aadhaar"}, bad)[2], "bad_aadhaar")

    def test_gstin_checksum_known_example(self):
        self.assertEqual(V.gstin_checksum("27AAPFU0939F1Z"), "V")
        self.assertTrue(V.validate({"type": "gstin"}, valid_gstin())[0])
        self.assertFalse(V.validate({"type": "gstin"}, "33ABCDE1234F1Z0" if valid_gstin()[-1] != "0" else "33ABCDE1234F1Z1")[0])

    def test_basic_formats(self):
        self.assertEqual(V.validate({"type": "mobile"}, "+91 98400 12345")[1], "9840012345")
        self.assertFalse(V.validate({"type": "mobile"}, "5840012345")[0])
        self.assertEqual(V.validate({"type": "pan"}, "abcde1234f")[1], "ABCDE1234F")
        self.assertTrue(V.validate({"type": "ifsc"}, "sbin0001234")[0])
        self.assertFalse(V.validate({"type": "ifsc"}, "SBIN1001234")[0])
        self.assertEqual(V.validate({"type": "vehicle_no"}, "tn 01 ab 1234")[1], "TN01AB1234")
        self.assertEqual(V.validate({"type": "pincode"}, "600 040")[1], "600040")

    def test_dates(self):
        today = date(2026, 10, 24)
        self.assertEqual(V.parse_date("15 Aug 1990", today), date(1990, 8, 15))
        self.assertEqual(V.parse_date("2026-03-01", today), date(2026, 3, 1))
        self.assertEqual(V.parse_date("today", today), today)
        self.assertEqual(V.validate({"type": "date", "rule": "past"}, "01/01/2030", today)[2], "date_future")
        self.assertEqual(V.validate({"type": "date", "rule": "adult"}, "01/01/2015", today)[2], "not_adult")
        self.assertEqual(V.validate({"type": "date", "rule": "within_months:3"}, "01/01/2026", today)[2], "date_out_of_range")

    def test_amounts(self):
        self.assertEqual(V.parse_amount("Rs. 1,50,000/-"), 150000)
        self.assertEqual(V.parse_amount("2.5 lakh"), 250000)
        self.assertEqual(V.parse_amount("50k"), 50000)
        self.assertEqual(V.amount_in_words(150000), "Rupees One Lakh Fifty Thousand Only")
        self.assertEqual(V.amount_in_words(12345678.5), "Rupees One Crore Twenty Three Lakh Forty Five Thousand Six Hundred Seventy Eight and Fifty Paise Only")
        self.assertEqual(V.format_inr(1500000), "15,00,000")

    def test_mask(self):
        self.assertEqual(V.mask({"type": "aadhaar"}, "2345 6789 0123"), "XXXX XXXX 0123")
        self.assertEqual(V.mask({"type": "mobile"}, "9840012345"), "9840012345")


class EngineTests(unittest.TestCase):
    def test_all_forms_load(self):
        forms = engine.all_forms()
        self.assertGreaterEqual(len(forms), 16)
        for form in forms.values():
            for lang in ("en", "ta", "hi", "or"):
                self.assertTrue(form["title"].get(lang), f"{form['id']} missing {lang} title")
            for f in form["fields"]:
                self.assertIn("type", f, f"{form['id']}.{f['id']}")
                if f["type"] in {"choice", "yesno"}:
                    self.assertGreaterEqual(len(f["options"]), 2)

    def test_show_if(self):
        form = engine.get_form("bank_savings_account")
        ids = [f["id"] for f in engine.visible_fields(form, {"nominee_wanted": "No"})]
        self.assertNotIn("nominee_name", ids)
        ids = [f["id"] for f in engine.visible_fields(form, {"nominee_wanted": "Yes"})]
        self.assertIn("nominee_name", ids)

    def test_computed(self):
        gst = engine.get_form("gst_pmt06_challan")
        comp = {c["id"]: c["value"] for c in engine.compute_values(gst, {"cgst_tax": 900, "sgst_tax": 900, "late_fee_total": 100})}
        self.assertEqual(comp["gst_total"], 1900)
        self.assertEqual(comp["late_fee_cgst"], 50)
        itr = engine.get_form("itr1_sahaj")
        comp = {c["id"]: c["value"] for c in engine.compute_values(itr, {"tax_regime": "Old regime", "gross_salary": 800000,
                                                                          "other_income": 10000, "deduction_80c": 200000})}
        self.assertEqual(comp["standard_deduction"], 50000)
        self.assertEqual(comp["taxable_income_estimate"], 800000 - 50000 + 10000 - 150000)  # 80C capped
        deed = engine.get_form("registration_deed")
        comp = {c["id"]: c["value"] for c in engine.compute_values(deed, {"deed_type": "Sale deed", "consideration_amount": 4000000,
                                                                           "guideline_value": 5000000})}
        self.assertEqual(comp["stamp_duty_estimate"], 350000)  # 7% of the higher guideline value

    def test_checks(self):
        rent = engine.get_form("rental_agreement")
        self.assertTrue(engine.run_checks(rent, {"purpose": "Residential", "monthly_rent": 10000, "security_deposit": 100000}))
        self.assertFalse(engine.run_checks(rent, {"purpose": "Residential", "monthly_rent": 10000, "security_deposit": 30000}))

    def test_load_estimate(self):
        kw, items = engine.estimate_load_kw("4 fans, 6 LED lights, 1 fridge and 1 AC")
        self.assertAlmostEqual(kw, (4 * 75 + 6 * 15 + 200 + 1500) / 1000, places=2)
        self.assertEqual(len(items), 4)
        self.assertIsNone(engine.estimate_load_kw("not sure"))

    def test_keyword_routing(self):
        self.assertEqual(engine.match_forms("I want a new gas cylinder")[0][0], "lpg_connection")
        self.assertIn(engine.match_forms("current connection for my shop")[0][0], {"eb_commercial"})


class RagTests(unittest.TestCase):
    def test_retrieve_filters_by_tag(self):
        hits = retrieve("how long is a cheque valid stale", tags=["bank_cheque"])
        self.assertTrue(hits)
        self.assertEqual(hits[0].tag, "bank_cheque")
        self.assertIn("three months", hits[0].text)


class VisionSchemaTests(unittest.TestCase):
    def test_vision_json_is_cleaned_and_mapped(self):
        schema = schema_from_vision_json({"title": "Ration card form", "fields": [
            {"id": "Applicant Name", "type": "name", "label": "Applicant name"},
            {"id": "mob", "type": "mobile", "label": "Mobile"},
            {"id": "cat", "type": "choice", "label": "Card type", "options": ["APL", "BPL"]},
            {"id": "x", "type": "weird", "label": "Something"},
        ]})
        self.assertEqual(schema["fields"][1], {"use": "mobile", "required": True})
        self.assertEqual(schema["fields"][3]["type"], "text")
        form = engine.register_custom_form(schema)
        self.assertTrue(form["id"].startswith("custom_"))

    def test_vision_boxes_are_kept_for_guided_fill(self):
        schema = schema_from_vision_json({"fields": [
            {"id": "name", "type": "name", "label": "Name", "box": [100, 200, 150, 900]},
            {"id": "mob", "type": "mobile", "label": "Mobile", "box": [200, 200, 240, 600]},
            {"id": "bad", "type": "text", "label": "Village", "box": [300, 500, 300, 400]},   # empty area
            {"id": "junk", "type": "text", "label": "Ward", "box": "top left"},
        ]})
        self.assertEqual(schema["fields"][0]["box"], {"x": 0.2, "y": 0.1, "w": 0.7, "h": 0.05})
        self.assertEqual(schema["fields"][1]["box"], {"x": 0.2, "y": 0.2, "w": 0.4, "h": 0.04})
        self.assertNotIn("box", schema["fields"][2])
        self.assertNotIn("box", schema["fields"][3])
        form = engine.register_custom_form(schema)
        self.assertEqual(engine.field_by_id(form, "mobile")["box"]["w"], 0.4)


# ----------------------------------------------------------------------------- end-to-end conversations
def sample_answer(field: dict) -> str:
    t = field["type"]
    if t in {"choice", "yesno"}:
        return "1" if t == "choice" else "yes"
    rule = field.get("rule", "")
    return {
        "name": "Ravi Kumar", "address": "12 Gandhi Street, Anna Nagar, Chennai", "text": "Chennai",
        "mobile": "9840012345", "email": "ravi@example.com", "pincode": "600040", "aadhaar": valid_aadhaar(),
        "pan": "ABCDE1234F", "ifsc": "SBIN0001234", "gstin": valid_gstin(), "account_number": "123456789012",
        "uan": "100200300400", "vehicle_no": "TN 01 AB 1234", "month_year": "09/2026",
        "amount": "25000",
        "number": str(min(max(field.get("min", 0), 2010 if field.get("min", 0) > 100 else 2), field.get("max", 10 ** 9))),
        "date": "today" if rule.startswith("within_months") else "15/08/2030" if rule == "future" else "15/08/1990",
    }[t]


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.sm = SessionManager()

    def answer_until_review(self, sid, overrides=None, limit=80):
        overrides = overrides or {}
        view = self.sm.view(sid)
        for _ in range(limit):
            if view["stage"] != "filling":
                return view
            form = engine.get_form(view["form"]["id"])
            field = engine.field_by_id(form, view["current_field"])
            view = self.sm.send(sid, overrides.get(field["id"], sample_answer(field)))
        self.fail("form never reached review")

    def test_every_form_end_to_end_with_pdf(self):
        for form_id in [f for f, form in engine.all_forms().items() if form["category"] != "custom"]:
            with self.subTest(form=form_id):
                view = self.sm.start(form_id, "en")
                self.assertEqual(view["stage"], "filling")
                view = self.answer_until_review(view["session_id"])
                self.assertEqual(view["stage"], "review")
                self.assertIn("Is everything correct", view["reply"])
                view = self.sm.send(view["session_id"], "yes")
                self.assertEqual(view["stage"], "complete")
                pdf, name = self.sm.pdf(view["session_id"])
                self.assertTrue(pdf.startswith(b"%PDF"), form_id)
                self.assertGreater(len(pdf), 1500)

    def test_validation_explain_skip_and_correction(self):
        view = self.sm.start("bank_savings_account", "en")
        sid = view["session_id"]
        self.assertIn("Which bank and branch", view["reply"])
        view = self.sm.send(sid, "SBI, Anna Nagar")
        view = self.sm.send(sid, "my name is ravi kumar")
        self.assertEqual(view["fields"][1]["value"], "Ravi Kumar")
        view = self.sm.send(sid, "what does this mean?")               # explain (RAG)
        self.assertIn("Here's what this means", view["reply"])
        self.assertEqual(view["current_field"], "father_or_spouse_name")
        view = self.sm.send(sid, "Mohan Kumar")
        view = self.sm.send(sid, "15/08/1990")
        view = self.sm.send(sid, "2")                                   # gender option 2
        self.assertEqual(next(f for f in view["fields"] if f["id"] == "gender")["value"], "Female")
        view = self.sm.send(sid, "married")
        view = self.sm.send(sid, "12345")                               # bad mobile
        self.assertIn("10 digits", view["reply"])
        view = self.sm.send(sid, "98400 12345")
        view = self.sm.send(sid, "skip")                                # optional email
        self.assertEqual(next(f for f in view["fields"] if f["id"] == "email")["status"], "skipped")
        view = self.sm.send(sid, "change my mobile number")             # correction mid-form
        self.assertEqual(view["current_field"], "mobile")
        view = self.sm.send(sid, "9123456780")
        self.assertEqual(view["current_field"], "address")
        view = self.answer_until_review(sid, {"nominee_wanted": "no", "pan": "skip"})
        self.assertNotIn("nominee_name", [f["id"] for f in view["fields"]])
        aadhaar_shown = next(f for f in view["fields"] if f["id"] == "aadhaar")["value"]
        self.assertTrue(aadhaar_shown.startswith("XXXX"))                # masked in API
        view = self.sm.send(sid, "no")                                  # not confirmed -> which field?
        view = self.sm.send(sid, "change occupation")
        self.assertEqual(view["stage"], "filling")
        view = self.sm.send(sid, "Teacher")
        self.assertEqual(view["stage"], "review")                       # back to review after fixing
        self.assertEqual(self.sm.send(sid, "yes")["stage"], "complete")

    def test_required_cannot_be_skipped(self):
        view = self.sm.start("bank_cheque", "en")
        view = self.sm.send(view["session_id"], "skip")
        self.assertIn("required", view["reply"])
        self.assertEqual(view["current_field"], "payee_name")

    def test_appliance_load_estimate_in_chat(self):
        sid = self.sm.start("eb_domestic", "en")["session_id"]
        view = self.answer_until_reaching(sid, "connected_load_kw")
        view = self.sm.send(sid, "4 fans, 6 lights, 1 fridge, 1 AC")
        self.assertIn("kW", view["history"][-1]["text"])
        self.assertEqual(next(f for f in view["fields"] if f["id"] == "connected_load_kw")["value"], "2.09")

    def answer_until_reaching(self, sid, target):
        view = self.sm.view(sid)
        while view["current_field"] != target:
            form = engine.get_form(view["form"]["id"])
            view = self.sm.send(sid, sample_answer(engine.field_by_id(form, view["current_field"])))
        return view

    def test_tamil_session_uses_native_questions(self):
        view = self.sm.start("lpg_connection", "ta")
        self.assertIn("LPG", view["reply"])
        sid = view["session_id"]
        view = self.sm.send(sid, "1")
        self.assertIn("முழுப் பெயர்", view["reply"])                    # common field asked in Tamil
        view = self.sm.send(sid, "ரவி குமார்")                           # Tamil script name, no LLM
        self.assertIn("ஆங்கில", view["reply"])                          # asked to type in English
        view = self.sm.send(sid, "Ravi Kumar")
        self.assertEqual(view["current_field"], "father_or_spouse_name")

    def test_free_text_intake(self):
        view = self.sm.start(None, "en")
        self.assertEqual(view["stage"], "pick_form")
        view = self.sm.send(view["session_id"], "I need to write a cheque to my landlord")
        self.assertEqual(view["form"]["id"], "bank_cheque")

    def test_delete_wipes_session(self):
        sid = self.sm.start("bank_cheque", "en")["session_id"]
        self.sm.delete(sid)
        with self.assertRaises(Exception):
            self.sm.view(sid)


if __name__ == "__main__":
    unittest.main()


class DisplayTests(unittest.TestCase):
    def test_amount_shown_in_indian_format(self):
        sm = SessionManager()
        sid = sm.start("bank_cheque", "en")["session_id"]
        sm.send(sid, "Lakshmi Traders")
        view = sm.send(sid, "125450")
        self.assertEqual(next(f for f in view["fields"] if f["id"] == "amount")["value"], "Rs. 1,25,450")


class MetricsTests(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        self.path = Path(os.environ["METRICS_FILE"])
        if self.path.exists():
            self.path.unlink()

    def test_completed_session_recorded_without_personal_data(self):
        from app import metrics
        sm = SessionManager()
        sid = sm.start("bank_cheque", "en")["session_id"]
        sm.send(sid, "skip", via="tap")                    # required - cannot skip, not counted as invalid
        sm.send(sid, "Lakshmi Traders", via="voice")
        sm.send(sid, "abc", via="text")                     # invalid amount
        sm.send(sid, "what does this mean?", via="tap")
        for text in ["125450", "today", "1", "yes"]:
            sm.send(sid, text, via="text")
        recs = metrics.load_records(self.path)
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertTrue(r["completed"])
        self.assertEqual(r["invalid_inputs"], 1)
        self.assertEqual(r["error_types"], {"bad_amount": 1})
        self.assertEqual(r["explains"], 1)
        self.assertEqual(r["via"], {"tap": 2, "voice": 1, "text": 5})
        raw = self.path.read_text()
        for secret in ["Lakshmi", "125450", "Traders"]:
            self.assertNotIn(secret, raw)                    # no answers stored
        sm.delete(sid)
        self.assertEqual(len(metrics.load_records(self.path)), 1)  # not written twice

    def test_abandoned_session_recorded_on_delete(self):
        from app import metrics
        sm = SessionManager()
        sid = sm.start("lpg_connection", "ta")["session_id"]
        sm.send(sid, "1")
        sm.delete(sid)
        recs = metrics.load_records(self.path)
        self.assertEqual(len(recs), 1)
        self.assertFalse(recs[0]["completed"])
        summary = metrics.summarize(recs)
        self.assertEqual(summary["completion_rate_pct"], 0.0)
        self.assertEqual(summary["by_language"], {"ta": 1})


class EvalHarnessTests(unittest.TestCase):
    def test_rules_mode_runs_and_labels_are_valid(self):
        from eval import run_eval
        run_eval.set_mode("rules")
        intent, _ = run_eval.eval_intent(run_eval.load("intent"))
        extraction, _ = run_eval.eval_extraction(run_eval.load("extraction"))
        rag, _ = run_eval.eval_rag(run_eval.load("rag"))     # raises if a label points to a missing note
        self.assertGreater(intent["n"], 80)
        self.assertEqual(extraction["invalid_inputs_rejected"], 100.0)
        self.assertGreaterEqual(rag["filtered_by_form"]["recall_at_3"], 90)


class OptionMatchingTests(unittest.TestCase):
    """Cases reported from real testing: English option words said or typed in Indian scripts."""

    def test_numbers_and_transliterated_words(self):
        from app.agents.nodes import match_option
        lpg = engine.field_by_id(engine.get_form("lpg_connection"), "connection_type")
        self.assertEqual(match_option(lpg, "14.2 கிலோ கிராம்ஸ் டொமஸ்டிக்", "ta", {}, use_llm=False), "Domestic 14.2 kg")
        self.assertEqual(match_option(lpg, "19 किलो वाला", "hi", {}, use_llm=False), "Commercial 19 kg")
        self.assertEqual(match_option(lpg, "கமர்ஷியல்", "ta", {}, use_llm=False), "Commercial 19 kg")
        self.assertIsNone(match_option(lpg, "domestic", "en", {}, use_llm=False))  # ambiguous: two domestic sizes
        phase = engine.field_by_id(engine.get_form("eb_domestic"), "phase")
        self.assertEqual(match_option(phase, "த்ரீ ஃபேஸ்", "ta", {}, use_llm=False), "Three phase")
