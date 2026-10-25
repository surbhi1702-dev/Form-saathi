# Form Saathi

A chat assistant that helps people fill Indian bank and government forms in Tamil, Hindi, Odia or English.

## Why it exists

Many people in India can't comfortably read an English form, or can't see the small print. To fill a bank slip, a KYC form or an electricity connection form, they rely on a middleman: a relative who has to sit with them, or an agent near the office who charges a fee. Form Saathi is an AI agent that does that middleman's job. It asks one question at a time in the person's own language, explains words like "sanctioned load" or "encumbrance", catches mistakes before the form reaches the counter, and can work entirely by voice.

## What it does

- You pick a language and a form, then answer questions by typing, tapping or speaking.
- A copy of the form on the right side fills in as you answer.
- Wrong inputs are caught immediately: invalid Aadhaar (Verhoeff checksum), PAN, IFSC, GSTIN (checksum), PIN, mobile number, impossible dates, a cheque older than 3 months, and so on.
- Ask "what does this mean?" on any question, and it answers from the department's rules (RAG) and shows where the answer came from.
- At the end you get a summary, warnings (for example, "deposit is more than 3 months' rent"), a checklist of documents to carry, and a PDF to copy from.
- For a form that isn't built in, you upload a photo of it and the vision model turns it into questions. This needs a Groq key with an image model; without one the upload button is turned off.
- Accessibility options: larger text, high-contrast colours, read-aloud, and a fully hands-free mode that reads each question, listens, and repeats the answer back.
- It works on phones and can be installed to the home screen like an app (PWA).

There are 16 forms right now: bank KYC, cash withdrawal, savings account, cheque, GST PMT-06 challan, ITR-1, EPF Form 11, job application, electricity (domestic and commercial), LPG, Metro water, property tax, registration deed, rental agreement and commercial vehicle permit.

## How it works

The backend is a LangGraph state graph. Each user message runs through it once, and a checkpointer keeps the session state between messages.

```mermaid
flowchart LR
    S([message]) --> R{route}
    R -->|no form yet| I[intake]
    R --> C{intent}
    I --> A[ask next question]
    C -->|answer| E[extract + validate]
    C -->|question| X[explain with RAG]
    C -->|skip| K[skip]
    C -->|change X| CO[correction]
    C -->|yes| F[finish]
    E -->|ok| ADV{more?}
    E -->|invalid| RE[re-ask with reason]
    K --> ADV
    ADV -->|yes| A
    ADV -->|no| RV[review]
    CO --> A
```

Some decisions and why I made them:

- **Validation is plain code, not the LLM.** A model can say a wrong Aadhaar number looks fine. Checksums can't. The LLM is only used where rules are weak: understanding free-text answers, transliterating names typed in Tamil, translating form-specific text, and writing explanations.
- **Every LLM call has a fallback.** If the Groq call fails, the graph still works with rules, and form-specific text stays in English. This also means the tests run offline.
- **Forms are JSON, not code.** Adding a form means writing one file in `backend/app/forms/schemas/`. Common fields such as name, mobile and Aadhaar come from a shared file that is already translated into all four languages.
- **BM25 instead of embeddings for RAG.** The knowledge notes are short and full of exact terms (PMT-06, OVD, 80C), where keyword search works well and needs no embedding model. The index is wrapped as a LangChain retriever, so it can be swapped for a vector store later.
- **Sensitive numbers are masked.** Aadhaar, PAN and account numbers only show the last 4 digits in the UI and in read-back. Sessions are in memory only and expire after 30 minutes.

Stack: Python, FastAPI, LangGraph, LangChain, Groq (Llama 3.3 70B by default, or `openai/gpt-oss-120b` when the key can't use Llama; a vision model such as Llama 4 Scout for photos, if the key has one), ReportLab for PDFs, and React with TypeScript and Vite for the frontend. Voice uses the browser's speech recognition and speech synthesis.

## Running it

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add a Groq API key (free at console.groq.com)
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

Tests (no API key needed):

```bash
cd backend
python -m pytest -q
```

To put it online (Render for the backend, Vercel for the frontend) and install it on a phone, see [DEPLOY.md](DEPLOY.md).

## Measuring it

```bash
cd backend
python -m eval.run_eval        # accuracy on labelled test sets, rules-only vs rules + LLM
python -m eval.usage_report    # anonymous usage numbers collected while people use the app
```

The evaluation covers intent routing, value extraction (including rejecting invalid values) and RAG retrieval, in all four languages, and writes `backend/eval/results/EVAL.md`. While people use the app it records only counts (time per form, invalid inputs caught, typed/tapped/spoken), never their answers. [TESTING.md](TESTING.md) has the manual test plan and a made-up test identity to use instead of real details.

The first evaluation run found a real bug: Hindi "हाँ" (yes) wasn't recognised, because splitting words with `\w` breaks Devanagari at vowel signs. A tester also found that "14.2 கிலோ டொமஸ்டிக்" (English words in Tamil script) didn't pick the 14.2 kg option. Both are fixed, with tests. Running it with Groq found a third: when the rules rejected an answer, the LLM retry could quietly "fix" it (fill in a missing digit or drop the digits from "Ravi 123"), so 1 of 10 invalid inputs got through. The retry now only counts if its value is actually in what the user typed.

The backend asks Groq which models your API key can use and falls back automatically if the configured one isn't available. `/api/health` shows which model is in use. The current evaluation ran on `openai/gpt-oss-120b`.

## Fine-tuning: plain-language simplifier

`finetune/` fine-tunes Qwen2.5-1.5B-Instruct with QLoRA to rewrite official form language into plain Tamil, Hindi, Odia and English.

- **Data** (`build_dataset.py`): 50 hand-written pairs plus 165 official sentences from the 16 forms and the knowledge notes, each rewritten by Groq (`openai/gpt-oss-120b`) into a jargon version and plain versions in all four languages. Filters drop pairs in the wrong script or that still contain jargon. 709 pairs, split by source sentence into 641 train and 68 test, so no test sentence is seen in training. Groq answers are saved to `data/generated.jsonl`, so the build resumes after the free tier's daily token limit.
- **Training** (`train_qlora.ipynb`, free Colab T4): base model in 4-bit NF4, LoRA rank 16 / alpha 32 / dropout 0.05 on all attention and MLP projections (about 18M trainable parameters, 1.2% of the model), loss only on the answer tokens, learning rate 2e-4 cosine, 3 epochs, effective batch 16, max length 384. The best epoch by test loss is kept (0.960, 0.885, 0.900, so epoch 2).
- **Evaluation** (`eval_simplifier.py`, run inside the notebook): the base model and the fine-tuned model, with the same prompt, on the 68 held-out sentences.

| | chrF (all) | chrF en | chrF ta | chrF hi | chrF or | Right script | Avg. words |
|---|---|---|---|---|---|---|---|
| Base Qwen2.5-1.5B | 8.1 | 31.6 | 0.4 | 0.3 | 0.2 | 25% | 29.9 |
| Fine-tuned (QLoRA) | **24.5** | **44.1** | **21.1** | **19.4** | **13.2** | **100%** | **12.0** |

Raw numbers: [`finetune/results/qwen2.5-1.5b-709pairs.json`](finetune/results/qwen2.5-1.5b-709pairs.json).

What this shows: the base model answers in English even when asked for Tamil, Hindi or Odia, so it is in the right script only 25% of the time. After fine-tuning it always answers in the requested script, its answers are less than half as long, and chrF against the reference plain sentence triples. Odia is the weakest language (chrF 13.2).

Limits, stated honestly: the test set is small (17 sentences per language), the reference sentences were written by an LLM and not yet checked by native speakers, and chrF measures closeness to one reference, not whether a reader understands the answer. The jargon-word rate was 0% for both models, so it did not separate them on this data. Next: finish generating the remaining ~250 sentences once Groq's daily limit resets, retrain, try Qwen2.5-3B/7B on a bigger GPU, and have native speakers rate a sample.

**Using it in the app:** run `python serve_simplifier.py --adapter ./formsaathi-simplifier-lora` and set `SIMPLIFIER_URL=http://localhost:8001/simplify` in `backend/.env`. When someone asks what a field means, Groq writes a grounded answer from the knowledge notes and the simplifier rewrites it in plain language in their language. If the simplifier is off or doesn't answer within 20 seconds, the app falls back to Groq's translation. The deployed demo doesn't run it, because a 1.5B model doesn't fit on Render's free plan.

## Status and what's next

- [ ] Run `eval.run_eval` with Groq and add the results table here
- [ ] Run the user study in TESTING.md and add the results
- [x] Run the fine-tuning and add the evaluation results here
- [ ] Finish the fine-tuning dataset (about 250 more sentences) and retrain
- [ ] Test the photo reader on real forms and measure how many fields it gets right
- [ ] Replace the built-in forms with field lists taken from the official forms (current ones are based on what these forms usually ask)
- [ ] Get the Tamil, Hindi and Odia text reviewed by native speakers
- [ ] Verify the rule notes in `backend/app/rag/knowledge/` against official sources; rates like stamp duty change

The PDF it generates is a draft to copy from. It is not the official form.

## Project structure

```
backend/app/
  agents/       graph.py, nodes.py, vision.py
  forms/        engine.py, common_fields.json, schemas/
  rag/          retriever.py, knowledge/
  pdf/          generator.py
  validators.py, i18n.py, llm.py, service.py, main.py
backend/tests/
frontend/src/
finetune/
```
