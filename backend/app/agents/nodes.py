"""The agents. Each node is a function FormState -> partial update, wired together in graph.py.

  Intake agent      - works out which form the user needs from free text
  Intent agent      - is this message an answer, a question, a skip, a correction, a confirmation?
  Extractor agent   - pulls the value out of a free-text answer (rules first, LLM fallback)
  Validator agent   - checks it (checksums, formats, date rules) and normalises it
  Explainer agent   - answers "what does this mean?" using RAG over department notes
  Interviewer agent - asks the next question in the user's language
  Correction agent  - handles "change my mobile number"
  Reviewer agent    - summary, cross-field warnings, documents checklist
  Translator        - shared helper that localises English-only text (cached per session)

Every LLM call has a deterministic fallback, so the graph runs (in English for
form-specific text) with no API key at all.
"""
from __future__ import annotations

import json
import logging
import re

from .. import i18n
from ..config import get_settings
from ..forms import engine
from ..i18n import loc, msg
from ..llm import chat_json, get_llm
from ..rag.retriever import retrieve
from ..validators import SENSITIVE_TYPES, is_latin, shown_value, validate

log = logging.getLogger("formsaathi.agents")
LANG_NAMES = {"en": "English", "ta": "Tamil", "hi": "Hindi", "or": "Odia"}

_YES = {"yes", "y", "yeah", "yep", "yup", "ok", "okay", "sure", "correct", "confirm", "haan", "ha", "han",
        "ஆம்", "ஆமா", "ஆமாம்", "சரி", "हाँ", "हां", "हा", "जी", "ठीक", "सही", "ହଁ", "ହଁ", "ଠିକ"}
_NO = {"no", "n", "nope", "nah", "nahi", "illai", "இல்லை", "வேண்டாம்", "नहीं", "नही", "ना", "ନା", "ନାହିଁ", "ନାହିଁ"}
_SKIP = {"skip", "pass", "none", "nil", "na", "n/a", "no email", "don't have", "dont have", "not applicable",
         "தவிர்", "தவிர்க்கவும்", "छोड़ो", "छोड़ें", "छोड़", "ଛାଡ", "ଛାଡନ୍ତୁ"}
_CHANGE = re.compile(r"\b(change|edit|modify|update|correct(?:ion)?|wrong|go back|mistake)\b|மாற்று|மாற்ற|தவறு|बदल|सुधार|गलत|ବଦଳ|ଭୁଲ", re.I)
# First word of an option -> how people commonly write/say it in Indian scripts.
_OPTION_HINTS = {
    "domestic": ("டொமஸ்டிக்", "டொமெஸ்டிக்", "வீட்டு", "डोमेस्टिक", "घरेलू", "ଡୋମେଷ୍ଟିକ", "ଘରୋଇ"),
    "commercial": ("கமர்ஷியல்", "கமர்சியல்", "வணிக", "कमर्शियल", "व्यावसायिक", "କମର୍ସିଆଲ", "ବ୍ୟବସାୟିକ"),
    "single": ("சிங்கிள்", "ஒற்றை", "सिंगल", "ସିଙ୍ଗଲ"),
    "three": ("த்ரீ", "மூன்று", "थ्री", "तीन", "ଥ୍ରୀ", "ତିନି"),
    "owner": ("ஓனர்", "உரிமையாளர்", "சொந்த", "ओनर", "मालिक", "ମାଲିକ"),
    "tenant": ("டெனன்ட்", "வாடகை", "टेनेंट", "किराय", "ଭଡାଟିଆ"),
    "residential": ("ரெசிடென்ஷியல்", "குடியிருப்பு", "रेसिडेंशियल", "आवासीय", "ଆବାସିକ"),
}
_SOFT = re.compile(r"\b(don'?t|do not|no|not|none|blank|later|nothing|n/a)\b|இல்லை|नहीं|ନାହିଁ", re.I)
_CHANGE_LEAD = re.compile(r"^\s*(please\s+|pls\s+)?(change|edit|modify|correct|go back)\b|மாற்று|बदल|ବଦଳ", re.I)
_QUESTION = re.compile(
    r"\?\s*$|^(what|why|how|which|where|meaning|explain|tell me about|i don'?t know|dont know|not sure)\b|"
    r"don'?t know|என்ன|ஏன்|எப்படி|அர்த்தம்|தெரியாது|क्या है|क्या होता|क्यों|कैसे|मतलब|पता नहीं|କ'ଣ|କଣ|କାହିଁକି|ଅର୍ଥ|ଜାଣିନି",
    re.I)


def _words(text: str) -> set[str]:
    """Split on spaces and punctuation, not on \\w: \\w breaks Indic words at vowel signs ("हाँ" -> "ह")."""
    return {w for w in re.split(r"[\s,.!?;:।|\"()]+", text) if w}


# ======================================================================= translator
def translate(text: str, lang: str, cache: dict) -> str:
    if lang == "en" or not text:
        return text
    key = f"{lang}::{text}"
    if key in cache:
        return cache[key]
    llm = get_llm()
    if llm.is_mock:
        return text
    out = llm.chat(
        f"Translate the user's text into simple, everyday {LANG_NAMES[lang]} that a person with little schooling "
        "understands. Keep numbers, codes and examples (PAN, IFSC, GSTIN, 15/08/1990, 'skip') unchanged. "
        "Reply with the translation only.", text)
    if out:
        cache[key] = out
    return out or text


def translate_many(texts: list[str], lang: str, cache: dict) -> list[str]:
    """Translate a list in one LLM call (review screen); falls back to per-item cache/English."""
    if lang == "en" or not texts:
        return texts
    missing = [t for t in texts if f"{lang}::{t}" not in cache]
    if missing and not get_llm().is_mock:
        data = chat_json(
            f"Translate each string into simple {LANG_NAMES[lang]}. Keep numbers and codes unchanged. "
            "Return a JSON array of strings in the same order.", json.dumps(missing, ensure_ascii=False))
        if isinstance(data, list) and len(data) == len(missing):
            for src, dst in zip(missing, data):
                cache[f"{lang}::{src}"] = str(dst)
    return [cache.get(f"{lang}::{t}", t) for t in texts]


# ======================================================================= helpers
def _form(state) -> dict | None:
    return engine.get_form(state.get("form_id") or "")


def field_label(field: dict, lang: str, cache: dict) -> str:
    label = field.get("label", field["id"])
    if i18n.has_translation(label, lang):
        return loc(label, lang)
    return translate(loc(label, "en"), lang, cache)


def option_display(field: dict, option: str, lang: str, cache: dict) -> str:
    if lang == "en":
        return option
    if field.get("type") == "yesno":
        return msg("yes" if option == "Yes" else "no", lang)
    native = field.get("option_labels", {}).get(option, {}).get(lang)
    if native:
        return f"{native} ({option})"
    translated = translate(option, lang, cache)
    return option if translated == option else f"{translated} ({option})"


def question_text(field: dict, lang: str, cache: dict) -> str:
    q = field.get("question") or {}
    if i18n.has_translation(q, lang):
        text = loc(q, lang)
    elif q:
        text = translate(loc(q, "en"), lang, cache)
    else:
        text = msg("generic_ask", lang, label=field_label(field, lang, cache))
    parts = [text]
    if not field.get("required", True):
        parts.append(msg("optional_hint", lang))
    if field.get("options"):
        opts = "\n".join(f"{i}. {option_display(field, o, lang, cache)}" for i, o in enumerate(field["options"], 1))
        parts.append(f"{msg('choose_option', lang)}\n{opts}")
    return "\n".join(parts)


def match_option(field: dict, text: str, lang: str, cache: dict, use_llm: bool = True) -> str | None:
    options = field.get("options") or []
    t = text.strip().lower().strip(".!। ")
    m = re.match(r"^(?:option\s*)?(\d{1,2})\b", t)
    if m and 1 <= int(m.group(1)) <= len(options):
        return options[int(m.group(1)) - 1]
    for opt in options:
        candidates = {opt.lower(), option_display(field, opt, lang, cache).lower()}
        native = field.get("option_labels", {}).get(opt, {}).get(lang)
        if native:
            candidates.add(native.lower())
        if t in candidates:
            return opt
    if set(options) >= {"Yes", "No"}:
        words = _words(t) | {t}
        if words & _NO:
            return "No"
        if words & _YES:
            return "Yes"
    hits = [o for o in options if o.lower() in t]
    if hits:
        return max(hits, key=len)
    # Numbers are script-independent: "14.2 கிலோ டொமஸ்டிக்" or "19 किलो वाला" -> the option containing 14.2 / 19.
    # Only used when exactly one option contains the number, and the number isn't a list position.
    nums = set(re.findall(r"\d+(?:\.\d+)?", t))
    if nums:
        by_num = [o for o in options if nums & set(re.findall(r"\d+(?:\.\d+)?", o))]
        if len(by_num) == 1:
            return by_num[0]
    # Common English words that people say in Tamil/Hindi/Odia script (spoken or typed).
    for opt in options:
        for hint in _OPTION_HINTS.get(opt.split()[0].lower(), ()):
            if hint in t and sum(any(h in t for h in _OPTION_HINTS.get(o.split()[0].lower(), ())) for o in options) == 1:
                return opt
    if len(t) >= 3:
        partial = [o for o in options if t in o.lower()]
        if len(partial) == 1:
            return partial[0]
    if not use_llm:
        return None
    data = chat_json(
        "Pick which option the user's reply means. Options: " + json.dumps(options, ensure_ascii=False) +
        '. Return {"option": "<exact option text>"} or {"option": null} if unclear.', text)
    if isinstance(data, dict) and data.get("option") in options:
        return data["option"]
    return None


_NAME_PREFIX = re.compile(r"^(my name is|name is|his name is|her name is|i am|i'm|this is|it is|it's|its|the name is)\s+", re.I)


def llm_extract(field: dict, text: str) -> str | None:
    """Ask the LLM to pull a clean value out of a messy answer, transliterating to English if needed."""
    hint = {"name": "a person's name in English (Latin) letters, transliterated if written in another script",
            "address": "the address in English (Latin) letters, transliterated if needed",
            "text": "the answer in English (Latin) letters, transliterated if needed"}.get(
        field.get("type"), f"the {field.get('type')} value only (digits/letters, no extra words)")
    data = chat_json(
        f"Extract {hint} from the user's reply to the question: '{loc(field.get('question'), 'en')}'. "
        'Return {"value": "..."} or {"value": null} if the reply doesn\'t contain it.', text)
    if isinstance(data, dict) and data.get("value") not in (None, ""):
        return str(data["value"])
    return None


def rule_candidate(field: dict, text: str, lang: str, cache: dict, notes: dict | None = None,
                   use_llm: bool = True) -> str:
    """Turn a raw reply into a value to validate, using rules (and the LLM only for options, if allowed)."""
    ftype = field.get("type")
    if ftype in {"choice", "yesno"}:
        return match_option(field, text, lang, cache, use_llm=use_llm) or ""
    if ftype == "number" and field.get("allow_appliances") and not re.fullmatch(
            r"\s*\d+(\.\d+)?\s*(kw|kilowatt)?\s*", text, re.I):
        est = engine.estimate_load_kw(text)
        if est:
            if notes is not None:
                notes[field["id"]] = "Estimated from: " + ", ".join(est[1])
            return str(est[0])
    if ftype == "name":
        return _NAME_PREFIX.sub("", text)
    return text


# ======================================================================= intake
def intake(state) -> dict:
    lang, text = state.get("lang", "en"), state.get("user_message", "")
    if text == "__start__":
        return {"reply_parts": [*state.get("reply_parts", []), msg("pick_form", lang)]}
    form_id = None
    llm = get_llm()
    if not llm.is_mock and text:
        catalog = {fid: loc(f["title"], "en") + " - " + loc(f["description"], "en") for fid, f in engine.all_forms().items()}
        data = chat_json("Which form does the user need? Forms: " + json.dumps(catalog) +
                         ' Return {"form_id": "<id>"} or {"form_id": null} if none fits.', text)
        if isinstance(data, dict) and data.get("form_id") in catalog:
            form_id = data["form_id"]
    if form_id is None:
        matches = engine.match_forms(text)
        form_id = matches[0][0] if matches else None
    if not form_id:
        return {"reply_parts": [*state.get("reply_parts", []), msg("pick_form", lang)]}
    form = engine.get_form(form_id)
    return {"form_id": form_id, "stage": "filling", "values": {}, "skipped": [],
            "reply_parts": [*state.get("reply_parts", []), msg("welcome", lang, form=loc(form["title"], lang))]}


# ======================================================================= intent
def classify(state) -> dict:
    text = (state.get("user_message") or "").strip()
    stage = state.get("stage")
    lower = text.lower().strip(".!। ")
    form = _form(state)
    field = engine.field_by_id(form, state.get("current_field")) if form else None

    if stage in {"review", "complete"}:
        if _CHANGE.search(text):
            return {"intent": "correct"}
        words = _words(lower) | {lower}
        if stage == "review" and words & _YES and not words & _NO:
            return {"intent": "confirm"}
        if stage == "complete":
            return {"intent": "info"}
        return {"intent": "correct"}

    # filling
    if lower in _SKIP or lower.startswith("skip"):
        return {"intent": "skip"}
    # Free-text answers may contain words like "update", so for those only a leading
    # "change ..." (or a native-language change word) counts as a correction.
    free_text = field and field.get("type") in {"text", "address", "name"}
    if _CHANGE.search(text) and (not free_text or _CHANGE_LEAD.search(text)):
        return {"intent": "correct"}
    # Confident rule decisions are final - no LLM call needed.
    if _QUESTION.search(text):
        return {"intent": "explain"}
    if field:
        valid = validate(field, rule_candidate(field, text, state.get("lang", "en"), {}, use_llm=False))[0]
        # A reply that already validates is an answer. Free text validates almost always,
        # so for those only trust it when there's no hint of skipping or changing.
        if valid and not (free_text and (_SOFT.search(text) or _CHANGE.search(text))):
            return {"intent": "answer"}

    # The rules aren't sure: ask the LLM.
    llm = get_llm()
    if not llm.is_mock and field:
        data = chat_json(
            "You route messages in a form-filling chat. The assistant just asked: "
            f"'{loc(field.get('question'), 'en')}'. Classify the user's reply as one of: "
            "answer (they gave the information), explain (they are asking what it means or how to find it), "
            "skip (they want to leave it blank), correct (they want to change an earlier answer). "
            'Return {"intent": "..."}', text)
        if isinstance(data, dict) and data.get("intent") in {"answer", "explain", "skip", "correct"}:
            return {"intent": data["intent"]}
    return {"intent": "answer"}


# ======================================================================= extractor + validator
def extract_validate(state) -> dict:
    form = _form(state)
    lang, cache = state.get("lang", "en"), dict(state.get("tcache", {}))
    field = engine.field_by_id(form, state.get("current_field")) or engine.next_field(
        form, state.get("values", {}), state.get("skipped", []))
    text = (state.get("user_message") or "").strip()
    notes = dict(state.get("notes", {}))
    ftype = field.get("type")
    candidate = rule_candidate(field, text, lang, cache, notes)
    if ftype in {"name", "address", "text"} and not is_latin(candidate) and field.get("latin_only", ftype in {"name", "address"}):
        candidate = llm_extract(field, text) or candidate

    ok, value, err = validate(field, candidate)
    if not ok and ftype not in {"choice", "yesno"} and not get_llm().is_mock:
        retry = llm_extract(field, text)
        if retry:
            ok, value, err = validate(field, retry)
    if not ok:
        return {"error": err, "tcache": cache, "current_field": field["id"]}

    values = dict(state.get("values", {}))
    values[field["id"]] = value
    values = engine.prune_hidden(form, values)
    skipped = [s for s in state.get("skipped", []) if s != field["id"]]
    parts = list(state.get("reply_parts", []))
    # Read the answer back so the user (or a listener in hands-free mode) can catch mistakes.
    # Sensitive numbers are only read back by their last 4 digits.
    if field.get("type") in SENSITIVE_TYPES:
        heard = msg("ending_in", lang, last4=re.sub(r"\D", "", str(value))[-4:] or str(value)[-4:])
    elif field.get("options"):
        heard = option_display(field, value, lang, cache)
    else:
        heard = shown_value(field, value)
    ack = msg("noted_value", lang, value=heard)
    if field["id"] in notes and field.get("allow_appliances"):
        ack = msg("noted_value", lang, value=f"{value} kW") + f" ({notes[field['id']]})"
    parts.append(ack)
    return {"values": values, "skipped": skipped, "error": None, "reply_parts": parts, "tcache": cache,
            "notes": notes, "current_field": None}


def reask(state) -> dict:
    """Validation failed: say what was wrong, then repeat the question."""
    form, lang, cache = _form(state), state.get("lang", "en"), dict(state.get("tcache", {}))
    field = engine.field_by_id(form, state.get("current_field"))
    parts = [*state.get("reply_parts", []), msg(state.get("error") or "empty", lang), question_text(field, lang, cache)]
    return {"reply_parts": parts, "tcache": cache}


# ======================================================================= explainer (RAG)
def explain(state) -> dict:
    form, lang, cache = _form(state), state.get("lang", "en"), dict(state.get("tcache", {}))
    settings = get_settings()
    field = engine.field_by_id(form, state.get("current_field")) or engine.next_field(
        form, state.get("values", {}), state.get("skipped", []))
    question = state.get("user_message", "")
    label_en = loc(field.get("label"), "en")
    chunks = retrieve(f"{question} {label_en} {field.get('explain', '')}", tags=form.get("knowledge_tags"), k=3)
    sources = sorted({f"{c.title} - {c.heading} ({c.source})" for c in chunks})
    llm = get_llm()
    answer = ""
    if not llm.is_mock:
        context = "\n\n".join(f"[{c.title} / {c.heading}]\n{c.text}" for c in chunks)
        target = "English" if settings.simplifier_url else LANG_NAMES[lang]
        answer = llm.chat(
            "You help people with little schooling fill Indian government and bank forms. Answer their question "
            f"about the field '{label_en}' on the form '{loc(form['title'], 'en')}'. Use ONLY the field note and "
            "the reference notes below; if they don't cover it, say what to ask at the office. "
            f"Use short sentences and everyday words, under 80 words, in {target}. No markdown.\n\n"
            f"Field note: {field.get('explain', '')}\n\nReference notes:\n{context}",
            question)
        if answer and settings.simplifier_url:
            answer = _simplify(answer, lang) or translate(answer, lang, cache)
    if not answer:
        answer = translate(field.get("explain") or label_en, lang, cache)
    parts = [*state.get("reply_parts", []), f"{msg('explain_prefix', lang)} {answer}", question_text(field, lang, cache)]
    return {"reply_parts": parts, "sources": sources, "tcache": cache, "current_field": field["id"]}


def _simplify(text: str, lang: str) -> str:
    """Optional: call the fine-tuned jargon->plain-language model (finetune/serve_simplifier.py)."""
    try:
        import requests

        r = requests.post(get_settings().simplifier_url, json={"text": text, "lang": lang}, timeout=20)
        r.raise_for_status()
        return r.json().get("plain", "")
    except Exception as exc:
        log.warning("Simplifier unavailable: %s", exc)
        return ""


# ======================================================================= skip / correct
def skip(state) -> dict:
    form, lang, cache = _form(state), state.get("lang", "en"), dict(state.get("tcache", {}))
    field = engine.field_by_id(form, state.get("current_field")) or engine.next_field(
        form, state.get("values", {}), state.get("skipped", []))
    if field.get("required", True):
        return {"error": "cannot_skip", "current_field": field["id"], "tcache": cache}
    return {"skipped": [*state.get("skipped", []), field["id"]], "current_field": None, "error": None,
            "reply_parts": [*state.get("reply_parts", []), msg("skipped", lang)]}


def correct(state) -> dict:
    form, lang, cache = _form(state), state.get("lang", "en"), dict(state.get("tcache", {}))
    text = (state.get("user_message") or "").lower()
    target = None
    # longest label match across all languages wins ("father's name" beats "name")
    best = 0
    for f in engine.visible_fields(form, state.get("values", {})):
        names = {f["id"].replace("_", " ")}
        label = f.get("label", {})
        names |= {v.lower() for v in label.values()} if isinstance(label, dict) else {str(label).lower()}
        for n in names:
            if n and n.lower() in text and len(n) > best:
                target, best = f, len(n)
    if target is None and not get_llm().is_mock:
        options = {f["id"]: loc(f.get("label"), "en") for f in engine.visible_fields(form, state.get("values", {}))}
        data = chat_json("The user wants to change one answer on a form. Fields: " + json.dumps(options) +
                         ' Return {"field_id": "<id>"} or {"field_id": null}.', state.get("user_message", ""))
        if isinstance(data, dict) and data.get("field_id") in options:
            target = engine.field_by_id(form, data["field_id"])
    if target is None:
        return {"target_field": None, "reply_parts": [*state.get("reply_parts", []), msg("which_field", lang)],
                "stage": state.get("stage")}
    values = {k: v for k, v in state.get("values", {}).items() if k != target["id"]}
    return {"target_field": target["id"], "values": values,
            "skipped": [s for s in state.get("skipped", []) if s != target["id"]],
            "stage": "filling", "current_field": target["id"], "tcache": cache,
            "reply_parts": [*state.get("reply_parts", []), msg("corrected", lang, label=field_label(target, lang, cache))]}


# ======================================================================= interviewer
def ask(state) -> dict:
    form, lang, cache = _form(state), state.get("lang", "en"), dict(state.get("tcache", {}))
    values, skipped = state.get("values", {}), state.get("skipped", [])
    field = engine.field_by_id(form, state.get("current_field"))
    if field is None or field["id"] in values or not engine.condition_met(field.get("show_if"), values):
        field = engine.next_field(form, values, skipped)
    if state.get("error") == "cannot_skip":
        parts = [*state.get("reply_parts", []), msg("cannot_skip", lang)]
    else:
        parts = list(state.get("reply_parts", []))
    parts.append(question_text(field, lang, cache))
    return {"current_field": field["id"], "reply_parts": parts, "tcache": cache, "error": None}


# ======================================================================= reviewer
def review(state) -> dict:
    form, lang, cache = _form(state), state.get("lang", "en"), dict(state.get("tcache", {}))
    values = state.get("values", {})
    lines = []
    for f in engine.visible_fields(form, values):
        if f["id"] in values:
            v = values[f["id"]]
            shown = option_display(f, v, lang, cache) if f.get("options") else shown_value(f, v)
            lines.append(f"- {field_label(f, lang, cache)}: {shown}")
    computed = engine.compute_values(form, values)
    comp_labels = translate_many([loc(c["label"], "en") for c in computed], lang, cache)
    for c, lbl in zip(computed, comp_labels):
        lines.append(f"- {lbl}: {engine.computed_display(c)}")
    warnings = translate_many(engine.run_checks(form, values), lang, cache)
    docs = translate_many(form.get("documents", []), lang, cache)
    parts = [*state.get("reply_parts", []), msg("review_intro", lang), "\n".join(lines)]
    if warnings:
        parts.append(msg("warnings_title", lang) + "\n" + "\n".join(f"! {w}" for w in warnings))
    if docs:
        parts.append(msg("documents_title", lang) + "\n" + "\n".join(f"- {d}" for d in docs))
    parts.append(msg("confirm_prompt", lang))
    return {"stage": "review", "current_field": None, "reply_parts": parts, "tcache": cache}


def finish(state) -> dict:
    return {"stage": "complete", "reply_parts": [*state.get("reply_parts", []), msg("completed", state.get("lang", "en"))]}


def info(state) -> dict:
    return {"reply_parts": [*state.get("reply_parts", []), msg("already_complete", state.get("lang", "en"))]}


def respond(state) -> dict:
    reply = "\n\n".join(p for p in state.get("reply_parts", []) if p)
    history = list(state.get("history", []))
    user = state.get("user_message", "")
    if user and user != "__start__":
        history.append({"role": "user", "text": user})
    history.append({"role": "assistant", "text": reply, "sources": state.get("sources", [])})
    return {"reply": reply, "history": history[-200:]}
