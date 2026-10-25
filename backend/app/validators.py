"""Deterministic parsers + validators for Indian form fields.

Each `parse_<type>(text)` pulls a candidate value out of free text (a user may say
"my number is 98400 12345").  `validate(field, value)` checks it and returns
(ok, normalised_value, error_code).  Error codes are translated in i18n.py.

These run *before* any LLM - structured fields (PAN, IFSC, Aadhaar...) never
depend on a model guessing correctly.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------- checksums
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_ok(number: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


_GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_checksum(first14: str) -> str:
    total = 0
    for i, ch in enumerate(first14):
        prod = _GST_CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += prod // 36 + prod % 36
    return _GST_CHARS[(36 - total % 36) % 36]


# ---------------------------------------------------------------- helpers
def digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def is_latin(text: str) -> bool:
    """True if text has no Indic/other non-Latin letters (official forms want English block letters)."""
    return all(ord(ch) < 0x0250 or not ch.isalpha() for ch in text)


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def parse_date(text: str, today: date | None = None) -> date | None:
    today = today or date.today()
    t = (text or "").strip().lower()
    if t in {"today", "இன்று", "आज", "ଆଜି"}:
        return today
    m = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", t)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.search(r"\b(\d{1,2})[-/. ](\d{1,2})[-/. ](\d{2,4})\b", t)
        if m:
            d, mo, y = map(int, m.groups())
        else:
            m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?[ -]*([a-z]{3,9})[ ,-]*(\d{2,4})\b", t)
            if not m or m.group(2)[:3] not in _MONTHS:
                return None
            d, mo, y = int(m.group(1)), _MONTHS[m.group(2)[:3]], int(m.group(3))
    if y < 100:
        y += 2000 if y <= today.year % 100 else 1900
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def parse_month_year(text: str) -> str | None:
    t = (text or "").strip().lower()
    m = re.search(r"\b(\d{1,2})[-/. ](\d{4})\b", t)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{int(m.group(1)):02d}/{m.group(2)}"
    m = re.search(r"\b([a-z]{3,9})[ ,-]*(\d{4})\b", t)
    if m and m.group(1)[:3] in _MONTHS:
        return f"{_MONTHS[m.group(1)[:3]]:02d}/{m.group(2)}"
    return None


_UNITS = {"crore": 10_000_000, "cr": 10_000_000, "lakh": 100_000, "lakhs": 100_000, "lac": 100_000,
          "lacs": 100_000, "l": 100_000, "thousand": 1000, "k": 1000}


def parse_amount(text: str) -> float | None:
    t = (text or "").lower().replace("₹", " ").replace("rs.", " ").replace("rs", " ").replace("/-", " ")
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(crore|cr|lakhs?|lacs?|thousand|k|l)?\b", t)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    if m.group(2):
        value *= _UNITS[m.group(2)]
    return round(value, 2)


def parse_number(text: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", (text or "").replace(",", ""))
    return float(m.group()) if m else None


# ---------------------------------------------------------------- amount in words (Indian system)
_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
         "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n: int) -> str:
    return _ONES[n] if n < 20 else (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else ""))


def _three(n: int) -> str:
    h, rest = divmod(n, 100)
    parts = []
    if h:
        parts.append(_ONES[h] + " Hundred")
    if rest:
        parts.append(_two(rest))
    return " ".join(parts)


def int_to_words_indian(n: int) -> str:
    if n == 0:
        return "Zero"
    parts = []
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    if crore:
        parts.append(int_to_words_indian(crore) + " Crore")
    if lakh:
        parts.append(_two(lakh) + " Lakh")
    if thousand:
        parts.append(_two(thousand) + " Thousand")
    if n:
        parts.append(_three(n))
    return " ".join(parts)


def amount_in_words(amount: float) -> str:
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    words = f"Rupees {int_to_words_indian(rupees)}"
    if paise:
        words += f" and {_two(paise)} Paise"
    return words + " Only"


def format_inr(amount: float) -> str:
    """1500000 -> '15,00,000' (Indian digit grouping)."""
    neg = amount < 0
    rupees, paise = divmod(round(abs(amount) * 100), 100)
    s = str(int(rupees))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
        s = f"{head},{tail}"
    out = f"{s}.{paise:02d}" if paise else s
    return ("-" if neg else "") + out


# ---------------------------------------------------------------- validation
def validate(field: dict, raw, today: date | None = None):
    """Return (ok, normalised_value, error_code)."""
    today = today or date.today()
    ftype = field.get("type", "text")
    text = str(raw).strip() if raw is not None else ""
    if not text:
        return False, None, "empty"

    if ftype in {"text", "name", "address", "textarea"}:
        if field.get("latin_only", ftype in {"name", "address"}) and not is_latin(text):
            return False, None, "needs_english"
        if ftype == "name":
            text = re.sub(r"\s+", " ", text).strip(" .,")
            if len(text) < 2 or re.search(r"\d", text):
                return False, None, "bad_name"
            return True, text.title() if text.islower() or text.isupper() else text, None
        if len(text) < field.get("min_length", 1):
            return False, None, "too_short"
        return True, re.sub(r"\s+", " ", text), None

    if ftype == "mobile":
        d = digits(text)
        if len(d) == 12 and d.startswith("91"):
            d = d[2:]
        if len(d) == 11 and d.startswith("0"):
            d = d[1:]
        return (True, d, None) if re.fullmatch(r"[6-9]\d{9}", d) else (False, None, "bad_mobile")

    if ftype == "pincode":
        d = digits(text)
        return (True, d, None) if re.fullmatch(r"[1-9]\d{5}", d) else (False, None, "bad_pincode")

    if ftype == "aadhaar":
        d = digits(text)
        if not re.fullmatch(r"[2-9]\d{11}", d) or not verhoeff_ok(d):
            return False, None, "bad_aadhaar"
        return True, f"{d[:4]} {d[4:8]} {d[8:]}", None

    if ftype == "pan":
        p = re.sub(r"\s", "", text).upper()
        return (True, p, None) if re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", p) else (False, None, "bad_pan")

    if ftype == "ifsc":
        p = re.sub(r"\s", "", text).upper()
        return (True, p, None) if re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", p) else (False, None, "bad_ifsc")

    if ftype == "gstin":
        g = re.sub(r"\s", "", text).upper()
        if not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", g) or gstin_checksum(g[:14]) != g[14]:
            return False, None, "bad_gstin"
        return True, g, None

    if ftype == "account_number":
        d = digits(text)
        return (True, d, None) if 9 <= len(d) <= 18 else (False, None, "bad_account")

    if ftype == "uan":
        d = digits(text)
        return (True, d, None) if len(d) == 12 else (False, None, "bad_uan")

    if ftype == "vehicle_no":
        v = re.sub(r"[\s-]", "", text).upper()
        if re.fullmatch(r"[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{4}", v) or re.fullmatch(r"\d{2}BH\d{4}[A-Z]{1,2}", v):
            return True, v, None
        return False, None, "bad_vehicle"

    if ftype == "email":
        e = text.lower()
        return (True, e, None) if re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", e) else (False, None, "bad_email")

    if ftype == "date":
        d = parse_date(text, today)
        if not d:
            return False, None, "bad_date"
        rule = field.get("rule", "")
        if rule == "past" and d > today:
            return False, None, "date_future"
        if rule == "future" and d < today:
            return False, None, "date_past"
        if rule == "adult" and (today - d).days < 18 * 365.25:
            return False, None, "not_adult"
        if rule.startswith("within_months:"):
            months = int(rule.split(":")[1])
            if d < today - timedelta(days=months * 30) or d > today + timedelta(days=months * 30):
                return False, None, "date_out_of_range"
        return True, d.strftime("%d/%m/%Y"), None

    if ftype == "month_year":
        v = parse_month_year(text)
        return (True, v, None) if v else (False, None, "bad_month_year")

    if ftype == "amount":
        a = parse_amount(text)
        if a is None:
            return False, None, "bad_amount"
        if a < field.get("min", 0) or ("max" in field and a > field["max"]):
            return False, None, "amount_range"
        return True, a, None

    if ftype == "number":
        n = parse_number(text)
        if n is None:
            return False, None, "bad_number"
        if n < field.get("min", 0) or ("max" in field and n > field["max"]):
            return False, None, "number_range"
        return True, int(n) if float(n).is_integer() else n, None

    if ftype in {"choice", "yesno"}:
        # choice matching happens in extraction; here we only check membership
        options = field.get("options", ["Yes", "No"])
        return (True, text, None) if text in options else (False, None, "bad_choice")

    return True, text, None


SENSITIVE_TYPES = {"aadhaar", "pan", "account_number", "uan"}


def mask(field: dict, value) -> str:
    """Mask sensitive values for display/logs: '1234 5678 9012' -> 'XXXX XXXX 9012'."""
    if value is None:
        return ""
    s = str(value)
    if field.get("type") in SENSITIVE_TYPES or field.get("sensitive"):
        visible = s[-4:]
        return re.sub(r"[A-Za-z0-9]", "X", s[:-4]) + visible
    return s


def display_value(field: dict, value) -> str:
    if field.get("type") == "amount" and isinstance(value, (int, float)):
        return "Rs. " + format_inr(value)
    return str(value)


def shown_value(field: dict, value) -> str:
    """What the user sees in chat/API: sensitive values masked, amounts as 'Rs. 1,25,450'."""
    if field.get("type") in SENSITIVE_TYPES or field.get("sensitive"):
        return mask(field, value)
    return display_value(field, value)


def now_str() -> str:
    return datetime.now().strftime("%d/%m/%Y")
