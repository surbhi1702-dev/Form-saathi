# Testing Form Saathi

There are two ways to get real numbers:

1. **Automatic evaluation** (`backend/eval/run_eval.py`) measures accuracy on labelled test sets. It takes about 10 minutes and needs no other people.
2. **Manual testing with real people.** The app records anonymous counts while people use it, so every test session adds to the numbers automatically.

---

## Part 1: Automatic evaluation

```bash
cd backend
python -m eval.run_eval
```

This runs every test twice, once with rules only and once with rules plus the Groq LLM, and writes `backend/eval/results/EVAL.md`. Every miss is listed in `failures_llm.jsonl` and `failures_rules.jsonl`. Read these: each miss is something to fix or to explain in an interview.

| Test set | File | What it checks |
|---|---|---|
| Intent | `eval/data/intent.jsonl` | Is a message an answer, a question, a skip or a correction? |
| Extraction | `eval/data/extraction.jsonl` | Is the right value pulled from a messy reply, and are invalid values rejected? |
| RAG | `eval/data/rag.jsonl` | Does the retriever find the right rule note for a question? |

**Make the test sets stronger.** The current examples were written by the person who built the app, which flatters it. Ask others to write new rows in their own words, especially in Tamil, Hindi and Odia. Each row is one line of JSON; copy an existing line and change the text and expected answer. Then run the evaluation again. Numbers measured on examples written by other people are much more convincing.

---

## Part 2: Manual testing

### Before you start

1. **Use the test identity below, never real details.** Answers are sent to Groq to be understood, so testers shouldn't type real Aadhaar, PAN or bank numbers.
2. **Start a fresh usage log** for this round:
   ```bash
   cd backend
   python -m eval.usage_report --reset
   ```
3. **Run the app** (backend and frontend), or use the deployed link on a phone.

### Test identity (made up; these pass the format checks)

| Field | Value |
|---|---|
| Name | Ravi Kumar |
| Father's name | Mohan Kumar |
| Date of birth | 15/08/1990 |
| Mobile | 9876543210 |
| Email | ravi.test@example.com |
| Address | 12 Gandhi Street, Anna Nagar, Chennai |
| PIN code | 600040 |
| Aadhaar | 2345 6789 0124 |
| PAN | ABCDE1234F |
| Bank account | 123456789012 |
| IFSC | SBIN0001234 |
| UAN | 100200300400 |
| GSTIN | 33ABCDE1234F1Z7 |
| Vehicle number | TN 01 AB 1234 |

Print this or keep it on a second screen.

---

### Round A: Bug hunt (one tester, about 3–4 hours, can be split over days)

Fill **every one of the 16 forms once**, changing how you answer each time. Tick each item and note anything odd in the bug log below.

**For each form:**
- [ ] It reaches the review screen and the "Ready" stamp
- [ ] The PDF downloads and opens, and the values in it match what you typed
- [ ] The documents list makes sense for that form

**Try these on at least a few forms:**
- [ ] Give a wrong value (a 9-digit mobile, a wrong Aadhaar digit, a future date of birth). It should explain the problem and ask again.
- [ ] Ask "what does this mean?" on a confusing question. The answer should make sense and show "Based on".
- [ ] Type "skip" on an optional question, and on a required one (it should refuse).
- [ ] Say "change my mobile number" partway through, and again on the review screen.
- [ ] Answer a choice question by number ("2"), by tapping, and by typing the option.
- [ ] Switch language partway through a form.
- [ ] Turn on Larger text, Clearer colours, Read aloud, and Speak and listen.
- [ ] Use the microphone to answer at least 5 questions.
- [ ] On a phone: install it to the home screen and fill one form.

**Bug log** (keep it in a sheet or notebook):

| # | Form | Language | What you did | What happened | What you expected | Screenshot |
|---|---|---|---|---|---|---|
| 1 | LPG | Tamil | Said "14.2 கிலோ டொமஸ்டிக்" | "I didn't catch that" | Pick Domestic 14.2 kg | yes |

That row is a real example from the first test, and it has already been fixed.

**What you get from Round A:** "Tested all 16 forms end-to-end in 4 languages; found and fixed N bugs." Count your bug log rows and fixes.

---

### Round B: Small user study (3–6 people, about 30 minutes each)

This is the most valuable test. Include people who find forms difficult, such as parents or relatives who don't read English well, or someone with weak eyesight. One person runs the session and takes notes; the other fills the forms.

**Before each session:** explain that you're testing the app, not them, and that they can stop any time. Ask if it's okay to note their time and mistakes. Don't record their name in your notes; use P1, P2 and so on.

**Tasks** (give the test identity card; they choose their language):
1. Fill the **Cheque writing helper** (short, 4 questions).
2. Fill the **LPG new connection** form.
3. Fill the **Bank KYC update** form.

**For each task, the note-taker writes down:**
- Whether they finished without help, with a little help, or not at all
- Where they got stuck (which question, and what confused them)
- Anything they said out loud ("what is this?", "I'm not sure")

The app records the time taken, invalid inputs caught, "what does this mean?" requests, and whether answers were typed, tapped or spoken. You don't need a stopwatch.

**After all three tasks, ask three questions** (score 1–5):
1. How easy was it to fill the forms? (1 = very hard, 5 = very easy)
2. Did you understand every question? (1 = not at all, 5 = completely)
3. Would you use this instead of asking someone for help? (1 = never, 5 = definitely)

Also ask one open question: "What should we change?"

**Optional comparison (makes the numbers much stronger):** before using the app, give the same person a **paper** cheque or form to fill on their own. Time it and count mistakes. Then compare with the app. For example: "Paper: 9 minutes, 3 mistakes. App: 5 minutes, 0 mistakes."

**Afterwards:**
```bash
cd backend
python -m eval.usage_report
```
This writes `backend/eval/results/USAGE.md` with completion rate, median time per form, invalid inputs caught, and the typed/tapped/spoken split.

**What you get from Round B:** a line like "In a pilot with 5 users (including 2 non-English readers), 14 of 15 forms were completed without help, with a median of 4.2 minutes per form; ease rated 4.4/5." Use your real numbers only.

---

### Round C: Photo reader (one tester, about 2 hours)

Needs a Groq key that has an image model available. Check `/api/health`: `vision_model` must not be empty.

1. Collect 10–20 **real blank forms** from different places: bank slips, college forms, government forms. Use blank ones only, not filled ones.
2. For each form, write down its real fields by hand (for example 12 fields).
3. Photograph it flat, in good light, and upload it with **Upload photo of form**.
4. Count:
   - Fields it found that are real (correct)
   - Real fields it missed
   - Fields it made up or got badly wrong

| Form | Real fields | Found correctly | Missed | Wrong/made up |
|---|---|---|---|---|
| SBI deposit slip | 9 | | | |

**Recall** = found correctly ÷ real fields. **Precision** = found correctly ÷ (found correctly + wrong).

**What you get from Round C:** "Form Reader extracted fields from 15 real forms with X% recall and Y% precision."

---

## Turning results into resume lines

Use only numbers you measured, and keep the files (`EVAL.md`, `USAGE.md`, your bug log and the photo table) in case an interviewer asks how you measured them.

| Source | Example line (fill in your numbers) |
|---|---|
| `EVAL.md` | "Hybrid rule + LLM routing reached X% intent accuracy on N multilingual messages (rules alone: Y%)" |
| `EVAL.md` | "RAG explainer found the correct rule in the top 3 for X% of N questions" |
| `EVAL.md` | "Answered X% of chat turns with no LLM call; median response Z ms" |
| Round A | "Tested all 16 forms in 4 languages; found and fixed N bugs" |
| Round B | "Pilot with N users: X% of forms completed without help, median M min per form" |
| Round C | "Read N real forms from photos with X% field recall" |
