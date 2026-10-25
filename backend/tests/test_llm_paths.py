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


if __name__ == "__main__":
    unittest.main()


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
