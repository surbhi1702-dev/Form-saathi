"""Exercise the LLM-backed code paths with a scripted fake model (no network)."""
import json
import os
import unittest

os.environ["FORMSAATHI_MOCK_LLM"] = "1"

from app import llm as llm_module  # noqa: E402
from app.agents.vision import read_form_image  # noqa: E402
from app.forms import engine  # noqa: E402
from app.service import SessionManager  # noqa: E402


class FakeLLM:
    is_mock = False
    vision_model = "fake-vision"

    def __init__(self):
        self.calls = []

    def chat(self, system, user, temperature=0.2):
        self.calls.append(system[:40])
        if "Translate each string" in system:
            return json.dumps([f"[ta] {s}" for s in json.loads(user)], ensure_ascii=False)
        if "Translate the user's text" in system:
            return f"[ta] {user}"
        if "Which form does the user need" in system:
            return '{"form_id": "metrowater_connection"}'
        if "Classify the user's reply" in system:
            return '{"intent": "explain"}' if "where" in user.lower() else '{"intent": "answer"}'
        if "Extract" in system:
            return '{"value": "Ravi Kumar"}' if "name" in system else '{"value": null}'
        if "Pick which option" in system:
            return '{"option": null}'
        if "Reference notes" in system:
            assert "property tax" in system.lower() or "metrowater" in system.lower()
            return "It is the number on your property tax receipt."
        return ""

    def vision(self, prompt, image_b64, mime):
        return json.dumps({"title": "Ration card application", "department": "Civil Supplies",
                           "fields": [{"id": "head", "type": "name", "label": "Head of family",
                                       "question": "Who is the head of the family?"},
                                      {"id": "m", "type": "mobile", "label": "Mobile"},
                                      {"id": "members", "type": "number", "label": "Family members"}],
                           "documents": ["Address proof"]})


class LLMPathTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeLLM()
        llm_module.set_llm(self.fake)
        os.environ["FORMSAATHI_MOCK_LLM"] = "0"
        os.environ["GROQ_API_KEY"] = "test-key"

    def tearDown(self):
        os.environ["FORMSAATHI_MOCK_LLM"] = "1"
        os.environ.pop("GROQ_API_KEY", None)
        llm_module.set_llm(None)

    def test_llm_intake_translation_extraction_and_rag_explain(self):
        sm = SessionManager()
        view = sm.start(None, "ta")
        view = sm.send(view["session_id"], "en veettukku thanni connection venum")
        self.assertEqual(view["form"]["id"], "metrowater_connection")
        sid = view["session_id"]
        view = sm.send(sid, "என் பெயர் ரவி குமார்")                     # Tamil name -> LLM transliterates
        self.assertEqual(view["fields"][0]["value"], "Ravi Kumar")
        # form-specific labels are translated through the LLM translator
        label = next(f["label"] for f in view["fields"] if f["id"] == "property_tax_assessment_no")
        self.assertTrue(label.startswith("[ta]"))
        # jump to the assessment number question and ask where to find it
        while view["current_field"] != "property_tax_assessment_no":
            fid = view["current_field"]
            ans = {"father_or_spouse_name": "Mohan Kumar", "mobile": "9840012345", "email": "skip",
                   "property_address": "12 Gandhi Street, Anna Nagar, Chennai", "pincode": "600040"}[fid]
            view = sm.send(sid, ans)
        view = sm.send(sid, "where do I find this number?")
        self.assertIn("property tax receipt", view["reply"])
        self.assertTrue(view["sources"])

    def test_vision_reader_registers_unseen_form(self):
        form = read_form_image(b"fake-bytes", "image/png")
        self.assertEqual(form["title"]["en"], "Ration card application")
        self.assertEqual(form["fields"][1]["id"], "mobile")             # mapped to multilingual common field
        sm = SessionManager()
        view = sm.start(form["id"], "en")
        self.assertIn("head of the family", view["reply"].lower())
        self.assertIsNotNone(engine.get_form(form["id"]))



class ModelPickingTests(unittest.TestCase):
    def test_falls_back_when_model_not_available(self):
        from app.llm import pick_models
        info = pick_models("llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct",
                           ["llama-3.1-8b-instant", "openai/gpt-oss-120b", "whisper-large-v3"])
        self.assertEqual(info["chat"], "openai/gpt-oss-120b")
        self.assertIsNone(info["vision"])
        self.assertEqual(len(info["warnings"]), 2)

    def test_keeps_configured_model_when_available(self):
        from app.llm import pick_models
        info = pick_models("llama-3.1-8b-instant", "v", ["llama-3.1-8b-instant"])
        self.assertEqual(info["chat"], "llama-3.1-8b-instant")
        self.assertEqual(info["warnings"][:0], [])


class GroundingTests(unittest.TestCase):
    """The LLM retry must not turn an invalid answer into a valid-looking one."""

    def setUp(self):
        self.fake = FakeLLM()
        llm_module.set_llm(self.fake)
        os.environ["FORMSAATHI_MOCK_LLM"] = "0"
        os.environ["GROQ_API_KEY"] = "test-key"

    def tearDown(self):
        os.environ["FORMSAATHI_MOCK_LLM"] = "1"
        os.environ.pop("GROQ_API_KEY", None)
        llm_module.set_llm(None)

    def extract(self, form_id, field_id, text, llm_value):
        from app.agents import nodes
        self.fake.chat = lambda system, user, temperature=0.2: json.dumps({"value": llm_value})
        state = {"form_id": form_id, "current_field": field_id, "user_message": text, "lang": "en",
                 "values": {}, "skipped": [], "tcache": {}, "notes": {}, "reply_parts": []}
        self.assertFalse(llm_module.get_llm().is_mock)
        return nodes.extract_validate(state)

    def test_llm_cannot_invent_digits(self):
        res = self.extract("bank_savings_account", "mobile", "98400 1234", "9840012345")
        self.assertIsNotNone(res["error"])
        res = self.extract("bank_savings_account", "aadhaar", "1234 5678 9012", "2345 6789 0124")
        self.assertIsNotNone(res["error"])

    def test_llm_cannot_strip_digits_from_name(self):
        res = self.extract("bank_savings_account", "full_name", "Ravi 123", "Ravi")
        self.assertIsNotNone(res["error"])

    def test_llm_cannot_fix_ifsc(self):
        res = self.extract("epf_form11", "ifsc", "SBIN1001234", "SBIN0001234")
        self.assertIsNotNone(res["error"])

    def test_grounded_retry_still_accepted(self):
        from app.agents.nodes import grounded
        self.assertTrue(grounded({"type": "mobile"}, "call me on 98400 12345 please", "9840012345"))
        self.assertTrue(grounded({"type": "pan"}, "pan: abcde 1234 f", "ABCDE1234F"))
        self.assertTrue(grounded({"type": "name"}, "naan Ravi Kumar", "Ravi Kumar"))


if __name__ == "__main__":
    unittest.main()
