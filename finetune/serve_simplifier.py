"""Serve the fine-tuned simplifier so the backend's Explainer agent can call it.

    pip install fastapi uvicorn transformers peft accelerate torch
    python serve_simplifier.py --adapter ./formsaathi-simplifier-lora          # fine-tuned
    python serve_simplifier.py --base-only --port 8002                        # baseline for eval

Then set SIMPLIFIER_URL=http://localhost:8001/simplify in backend/.env.
The Explainer agent then drafts a grounded explanation with Groq (RAG) in English and hands
it to this model to turn into plain Tamil/Hindi/Odia/English.
"""
import argparse

import torch
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

SYSTEM = ("You rewrite official Indian form language into short, plain sentences that a person with little "
          "schooling understands. Answer in the language given in brackets. Keep numbers and codes unchanged.")

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="Qwen/Qwen2.5-1.5B-Instruct")
ap.add_argument("--adapter", default="./formsaathi-simplifier-lora")
ap.add_argument("--base-only", action="store_true")
ap.add_argument("--port", type=int, default=8001)
args = ap.parse_args()

device = "cuda" if torch.cuda.is_available() else "cpu"
tok = AutoTokenizer.from_pretrained(args.base)
model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.float16 if device == "cuda" else torch.float32)
if not args.base_only:
    from peft import PeftModel

    model = PeftModel.from_pretrained(model, args.adapter)
model.to(device).eval()

app = FastAPI(title="Form Saathi simplifier")


class Req(BaseModel):
    text: str
    lang: str = "en"


@app.post("/simplify")
def simplify(req: Req):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"[{req.lang}] {req.text[:2000]}"}]
    prompt = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    enc = tok(prompt, return_tensors="pt", add_special_tokens=False).to(device)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=200, do_sample=False, repetition_penalty=1.1)
    return {"plain": tok.decode(out[0][enc["input_ids"].shape[-1]:], skip_special_tokens=True).strip()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=args.port)
