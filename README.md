# Form Saathi

A chat assistant that helps people fill Indian bank and government forms in Tamil, Hindi, Odia or English.

## Why it exists

Many people in India can't comfortably read an English form, or can't see the small print. To fill a bank slip, a KYC form or an electricity connection form, they rely on a middleman: a relative who has to sit with them, or an agent near the office who charges a fee. Form Saathi is an AI agent that does that middleman's job. It asks one question at a time in the person's own language, explains words like "sanctioned load" or "encumbrance", catches mistakes before the form reaches the counter, and can work entirely by voice.

## What it does

- You pick a language and a form, then answer questions by typing, tapping or speaking.
- A copy of the form on the right side fills in as you answer.
- Wrong inputs are caught immediately: invalid Aadhaar (Verhoeff checksum), PAN, IFSC, GSTIN (checksum), PIN, mobile number, impossible dates, a cheque older than 3 months, and so on.
- Ask "what does this mean?" on any question, and it answers from the department's rules (RAG) and shows where the answer came from.
- At the end you get a summary, warnings (for example, "deposit is more than 3 months' rent"), a checklist of documents to carry, and a PDF.
- **Guided fill on the paper form.** Someone who can't read English or small print can't copy a PDF onto the official form, so "Fill the paper form with me" walks through it one box at a time: the box is highlighted on the photo, the answer is shown letter by letter in large tiles, and it is read aloud in the person's language (with a "spell it letter by letter" button).
- For a form that isn't built in, you photograph the blank paper form. The vision model reads its questions and where each answer goes, so the guided fill can point at the exact box on that photo. The photo stays in the browser; only the server's reading of it is kept, in memory, for the session.
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

Stack: Python, FastAPI, LangGraph, LangChain, Groq (Llama 3.3 70B by default, or `openai/gpt-oss-120b` when the key can't use Llama; and Google Gemini Flash-Lite with a free key for reading photos of forms, or a Groq vision model if the key has one), ReportLab for PDFs, and React with TypeScript and Vite for the frontend. Voice uses the browser's speech recognition and speech synthesis.

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

## Fine-tuning (in progress)

`finetune/` has a pipeline to fine-tune Qwen2.5-1.5B with QLoRA. The goal is a model that rewrites official form language into plain Tamil, Hindi, Odia and English.

- `build_dataset.py` builds jargon-to-plain pairs. There are 50 hand-written seed pairs, and the rest are generated from the sentences in the forms and the knowledge notes.
- `train_qlora.ipynb` trains on Colab.
- `serve_simplifier.py` serves the trained model.
- `eval_simplifier.py` compares it with the base model using chrF, the share of answers still containing jargon, and whether the answer is in the right script.

## Status and what's next

- [ ] Run `eval.run_eval` with Groq and add the results table here
- [ ] Run the user study in TESTING.md and add the results
- [ ] Run the fine-tuning and add the evaluation results here
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
