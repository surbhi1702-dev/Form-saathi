"""Form engine: loads JSON form definitions and answers 'what's next?' questions.

Forms are data, not code. A form JSON lists fields; a field is either
  {"use": "mobile"}                     -> pulled from common_fields.json (already translated)
  {"id": "...", "type": "...", ...}     -> form-specific field
Optional keys: required (default true), show_if, options, rule, min/max, latin_only.
"""
from __future__ import annotations

import copy
import json
import re
import uuid
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from ..config import get_settings
from ..validators import amount_in_words, format_inr, parse_date

FORMS_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = FORMS_DIR / "schemas"
CATEGORIES = ["bank", "utilities", "property", "tax", "employment", "transport", "custom"]

_custom_forms: dict[str, dict] = {}


@lru_cache(maxsize=1)
def common_fields() -> dict:
    return json.loads((FORMS_DIR / "common_fields.json").read_text(encoding="utf-8"))


def _resolve_field(raw: dict) -> dict:
    if "use" in raw:
        base = copy.deepcopy(common_fields()[raw["use"]])
        base["id"] = raw["use"]
        base.update({k: v for k, v in raw.items() if k != "use"})
        field = base
    else:
        field = copy.deepcopy(raw)
    field.setdefault("required", True)
    if field.get("type") == "yesno":
        field.setdefault("options", ["Yes", "No"])
    return field


def _resolve_form(raw: dict) -> dict:
    form = copy.deepcopy(raw)
    form["fields"] = [_resolve_field(f) for f in raw["fields"]]
    form.setdefault("computed", [])
    form.setdefault("checks", [])
    form.setdefault("documents", [])
    form.setdefault("keywords", [])
    form.setdefault("knowledge_tags", [])
    form.setdefault("output", "form")
    ids = [f["id"] for f in form["fields"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate field ids in form {form['id']}")
    return form


@lru_cache(maxsize=1)
def _builtin_forms() -> dict[str, dict]:
    forms = {}
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        form = _resolve_form(json.loads(path.read_text(encoding="utf-8")))
        forms[form["id"]] = form
    return forms


def all_forms() -> dict[str, dict]:
    return {**_builtin_forms(), **_custom_forms}


def get_form(form_id: str) -> dict | None:
    return all_forms().get(form_id)


def register_custom_form(schema: dict) -> dict:
    """Register a form produced by the vision agent from a photo. Lives in memory only."""
    schema = copy.deepcopy(schema)
    schema["id"] = f"custom_{uuid.uuid4().hex[:8]}"
    schema["category"] = "custom"
    schema.setdefault("output", "form")
    form = _resolve_form(schema)
    _custom_forms[form["id"]] = form
    return form


# ---------------------------------------------------------------- visibility & progress
def condition_met(cond: dict | None, values: dict) -> bool:
    if not cond:
        return True
    current = values.get(cond["field"])
    if "equals" in cond:
        return current == cond["equals"]
    if "not_equals" in cond:
        return current is not None and current != cond["not_equals"]
    if "in" in cond:
        return current in cond["in"]
    return True


def visible_fields(form: dict, values: dict) -> list[dict]:
    return [f for f in form["fields"] if condition_met(f.get("show_if"), values)]


def field_by_id(form: dict, field_id: str | None) -> dict | None:
    return next((f for f in form["fields"] if f["id"] == field_id), None)


def next_field(form: dict, values: dict, skipped: list[str]) -> dict | None:
    for f in visible_fields(form, values):
        if f["id"] not in values and f["id"] not in skipped:
            return f
    return None


def prune_hidden(form: dict, values: dict) -> dict:
    """If an answer changed and a conditional field is no longer visible, drop its stale value."""
    visible = {f["id"] for f in visible_fields(form, values)}
    return {k: v for k, v in values.items() if k in visible}


def progress(form: dict, values: dict, skipped: list[str]) -> tuple[int, int]:
    vis = visible_fields(form, values)
    done = sum(1 for f in vis if f["id"] in values or f["id"] in skipped)
    return done, len(vis)


# ---------------------------------------------------------------- computed values
def _num(values: dict, key: str) -> float:
    v = values.get(key)
    return float(v) if isinstance(v, (int, float)) else 0.0


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise ValueError("bad date")


def _std_deduction(values: dict, regime_key: str, salary_key: str) -> float:
    cap = 75000 if values.get(regime_key) == "New regime" else 50000
    return min(cap, _num(values, salary_key))


def _deed_base(values: dict, type_key: str, cons_key: str, guide_key: str):
    if values.get(type_key) != "Sale deed":
        return None
    return max(_num(values, cons_key), _num(values, guide_key))


def compute_values(form: dict, values: dict) -> list[dict]:
    """Returns [{'id','label','value','kind'}] for derived fields such as amount in words."""
    s = get_settings()
    out = []
    for c in form.get("computed", []):
        fn, args = c["fn"], c["args"]
        if any(a not in values for a in args) and fn not in {"sum", "amount_in_words_of_sum", "itr_gross_total", "itr_taxable"}:
            continue
        kind, value = "amount", None
        if fn == "amount_in_words":
            kind, value = "text", amount_in_words(_num(values, args[0]))
        elif fn == "half":
            value = round(_num(values, args[0]) / 2, 2)
        elif fn == "sum":
            value = round(sum(_num(values, a) for a in args), 2)
        elif fn == "amount_in_words_of_sum":
            kind, value = "text", amount_in_words(round(sum(_num(values, a) for a in args), 2))
        elif fn == "add_months":
            d = parse_date(str(values[args[0]]))
            if d:  # a tenancy starting 01/11 for 11 months ends on 30/09, the day before the anniversary
                end = _add_months(d, int(_num(values, args[1]))) - timedelta(days=1)
                kind, value = "text", end.strftime("%d/%m/%Y")
        elif fn == "itr_standard_deduction":
            value = _std_deduction(values, args[0], args[1])
        elif fn == "itr_gross_total":
            if args[1] not in values:
                continue
            value = max(0.0, _num(values, args[1]) - _std_deduction(values, args[0], args[1])) + \
                _num(values, args[2]) + _num(values, args[3])
        elif fn == "itr_taxable":
            if args[1] not in values:
                continue
            gross = max(0.0, _num(values, args[1]) - _std_deduction(values, args[0], args[1])) + \
                _num(values, args[2]) + _num(values, args[3])
            deductions = 0.0
            if values.get(args[0]) == "Old regime":
                deductions = min(150000.0, _num(values, args[4])) + _num(values, args[5])
            value = max(0.0, gross - deductions)
        elif fn in {"stamp_duty", "registration_fee"}:
            base = _deed_base(values, *args)
            if base is None:
                kind, value = "text", "Depends on the relationship - check the current rate at the Sub-Registrar office"
            else:
                pct = s.stamp_duty_percent if fn == "stamp_duty" else s.registration_fee_percent
                value = round(base * pct / 100)
        if value is not None:
            out.append({"id": c["id"], "label": c["label"], "value": value, "kind": kind})
    return out


def computed_display(item: dict) -> str:
    return "Rs. " + format_inr(item["value"]) if item["kind"] == "amount" else str(item["value"])


# ---------------------------------------------------------------- cross-field checks (English; translated later)
def run_checks(form: dict, values: dict, today: date | None = None) -> list[str]:
    today = today or date.today()
    warnings = []
    for check in form.get("checks", []):
        if check == "gst_cgst_sgst_equal":
            if _num(values, "cgst_tax") != _num(values, "sgst_tax"):
                warnings.append("CGST and SGST are usually equal for sales within your state. Please confirm the split.")
        elif check == "cheque_validity":
            d = parse_date(str(values.get("cheque_date", "")))
            if d and d > today:
                warnings.append("This is a post-dated cheque - the bank will pay it only on or after that date.")
        elif check == "itr1_eligibility":
            total = _num(values, "gross_salary") + _num(values, "house_property_income") + _num(values, "other_income")
            if total > 5_000_000:
                warnings.append("ITR-1 is only for total income up to Rs. 50 lakh. With this income you will likely need ITR-2.")
            if _num(values, "tds") > 0 and _num(values, "gross_salary") == 0:
                warnings.append("TDS is entered but salary is 0 - check Form 16 / 26AS.")
        elif check == "lpg_household" and values.get("existing_lpg_in_household") == "Yes":
            warnings.append("Domestic LPG is normally one connection per household. The distributor may reject a second connection at the same address.")
        elif check == "deed_value_below_guideline":
            if values.get("deed_type") == "Sale deed" and _num(values, "consideration_amount") < _num(values, "guideline_value"):
                warnings.append("The sale price is below the guideline value, so stamp duty will be charged on the guideline value.")
        elif check == "rent_deposit_cap":
            rent, dep = _num(values, "monthly_rent"), _num(values, "security_deposit")
            months = 3 if values.get("purpose") == "Residential" else 6
            if rent and dep > months * rent:
                warnings.append(f"The deposit is more than {months} months' rent. Tamil Nadu's tenancy law caps deposits at "
                                f"{months} months' rent for {values.get('purpose', '').lower()} property - check your state's rule.")
    return warnings


# ---------------------------------------------------------------- helpers used by agents
def match_forms(text: str, limit: int = 3) -> list[tuple[str, int]]:
    """Cheap keyword router used when no LLM is available."""
    t = (text or "").lower()
    scores = []
    for fid, form in all_forms().items():
        score = sum(len(k) for k in form.get("keywords", []) if k.lower() in t)
        if score:
            scores.append((fid, score))
    return sorted(scores, key=lambda x: -x[1])[:limit]


_APPLIANCES = [  # (keywords, watts) - typical ratings, used only for a rough estimate
    (["ceiling fan", "fan", "மின்விசிறி", "ஃபேன்", "पंखा", "फैन", "ପଙ୍ଖା"], 75),
    (["tube light", "tubelight", "டியூப் லைட்", "ट्यूबलाइट"], 40),
    (["light", "led", "bulb", "lamp", "விளக்கு", "பல்பு", "बल्ब", "लाइट", "ବଲ୍ବ", "ଲାଇଟ"], 15),
    (["refrigerator", "fridge", "ஃப்ரிட்ஜ்", "फ्रिज", "ଫ୍ରିଜ"], 200),
    (["air conditioner", "ac", "ஏசி", "एसी", "ଏସି"], 1500),
    (["television", "tv", "டிவி", "टीवी", "ଟିଭି"], 100),
    (["washing machine", "வாஷிங் மெஷின்", "वॉशिंग मशीन"], 500),
    (["geyser", "water heater", "ஹீட்டர்", "गीजर"], 2000),
    (["wet grinder", "grinder", "கிரைண்டர்"], 500),
    (["mixer", "மிக்ஸி", "मिक्सी"], 750),
    (["iron box", "iron", "அயர்ன்", "प्रेस"], 1000),
    (["motor", "pump", "மோட்டார்", "मोटर", "ମୋଟର"], 750),
    (["microwave", "oven"], 1200),
    (["induction"], 1800),
    (["computer", "laptop", "கம்ப்யூட்டர்", "कंप्यूटर"], 150),
    (["cooler", "कूलर"], 200),
]


def estimate_load_kw(text: str) -> tuple[float, list[str]] | None:
    """'4 fans, 1 fridge, 1 AC' -> (2.0, ['4 x fan (75 W)', ...]). None if no appliances found."""
    t = " " + (text or "").lower() + " "
    total, items = 0, []
    for words, watts in _APPLIANCES:
        alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
        # one or more keywords of the same appliance in a row ("LED lights", "ceiling fans") count once
        pattern = rf"(?:(\d+)\s*(?:x\s*)?)?(?<![a-z])(?:{alt})s?(?:\s+(?:{alt})s?)*(?![a-z])"
        for m in re.finditer(pattern, t):
            count = int(m.group(1)) if m.group(1) else 1
            total += count * watts
            items.append(f"{count} x {words[0]} ({watts} W)")
        t = re.sub(pattern, " ", t)
    if not items:
        return None
    return round(max(total / 1000, 0.1), 2), items
