"""Form Reader agent: turns a photo of a form it has never seen into a Form Saathi schema.

The vision model proposes fields; this module validates and cleans them, and maps
common fields (mobile, Aadhaar, PAN...) onto the shared multilingual field library,
so even an unseen form gets native-language questions for those fields.

Each field also keeps the position of its writing space on the photo ("box", fractions
of the image width/height), so the guided-fill screen can point at the box to write in.
"""
from __future__ import annotations

import base64
import re

from ..forms import engine
from ..llm import get_llm, get_vision, parse_json

ALLOWED_TYPES = {"text", "name", "address", "date", "mobile", "email", "pincode", "aadhaar", "pan", "ifsc",
                 "gstin", "account_number", "uan", "vehicle_no", "amount", "number", "choice", "yesno", "month_year"}
COMMON_BY_TYPE = {"mobile": "mobile", "aadhaar": "aadhaar", "pan": "pan", "ifsc": "ifsc", "pincode": "pincode",
                  "email": "email", "account_number": "account_number"}

PROMPT = """You are reading a photo of an Indian application form (bank, government, utility...).
List every field the applicant must fill, in order. Skip office-use-only sections and signature boxes.
Return JSON only:
{"title": "...", "department": "...", "fields": [
  {"id": "snake_case_id", "type": "<one of: %s>", "label": "label as printed",
   "question": "a short, friendly question asking for this", "explain": "one plain sentence on what it means",
   "required": true, "options": ["only for choice fields"],
   "box": [ymin, xmin, ymax, xmax]}
 ], "documents": ["documents the form says to attach"]}
"box" is where the applicant writes the answer on the photo (the blank line, the row of letter boxes,
or the tick boxes - not the printed label), as integers from 0 to 1000 relative to the image height (y)
and width (x). Keep fields in the order they appear on the page, top to bottom.
Use type "name" for person names, "address" for addresses, "choice" when the form shows tick boxes.""" % ", ".join(sorted(ALLOWED_TYPES))


class FormReadError(Exception):
    pass


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s[:40] or "field"


def parse_box(raw) -> dict | None:
    """[ymin, xmin, ymax, xmax] on a 0-1000 grid -> {"x", "y", "w", "h"} as fractions of the image, or None."""
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    try:
        y0, x0, y1, x1 = (min(max(float(v), 0.0), 1000.0) / 1000 for v in raw)
    except (TypeError, ValueError):
        return None
    if y1 - y0 < 0.003 or x1 - x0 < 0.003:
        return None
    return {"x": round(x0, 4), "y": round(y0, 4), "w": round(x1 - x0, 4), "h": round(y1 - y0, 4)}


def schema_from_vision_json(data: dict) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("fields"), list) or not data["fields"]:
        raise FormReadError("Could not find any fields in the image.")
    fields, seen = [], set()
    for raw in data["fields"][:40]:
        if not isinstance(raw, dict):
            continue
        ftype = raw.get("type") if raw.get("type") in ALLOWED_TYPES else "text"
        box = parse_box(raw.get("box"))
        common = COMMON_BY_TYPE.get(ftype)
        if common and common not in seen:
            seen.add(common)
            fields.append({"use": common, "required": bool(raw.get("required", True)), **({"box": box} if box else {})})
            continue
        fid = _slug(raw.get("id") or raw.get("label"))
        while fid in seen:
            fid += "_2"
        seen.add(fid)
        label = str(raw.get("label") or fid.replace("_", " ").title())
        field = {"id": fid, "type": ftype, "label": {"en": label},
                 "question": {"en": str(raw.get("question") or f"What is your {label.lower()}?")},
                 "explain": str(raw.get("explain") or ""), "required": bool(raw.get("required", True))}
        if box:
            field["box"] = box
        if ftype in {"text", "address"}:
            field["latin_only"] = True
        if ftype == "choice":
            opts = [str(o) for o in (raw.get("options") or []) if str(o).strip()]
            if len(opts) < 2:
                field["type"] = "text"
            else:
                field["options"] = opts[:10]
        fields.append(field)
    title = str(data.get("title") or "Scanned form")
    return {"title": {"en": title}, "description": {"en": "Read from your photo by Form Saathi."},
            "department": str(data.get("department") or ""), "fields": fields,
            "documents": [str(d) for d in (data.get("documents") or [])][:15],
            "keywords": [], "knowledge_tags": [],
            "submit_note": "This form was read from a photo. Check every field against the paper form before submitting."}


def read_form_image(image_bytes: bytes, mime: str) -> dict:
    if get_llm().is_mock:
        raise FormReadError("Reading a new form from a photo needs the AI model. Add GROQ_API_KEY to backend/.env.")
    reader = get_vision()
    if reader is None:
        raise FormReadError("No image-reading model is set up, so photos of forms can't be read yet. Add a free "
                            "GEMINI_API_KEY to the backend settings. The built-in forms still work.")
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise FormReadError("Please upload a JPG, PNG or WEBP photo of the form.")
    if len(image_bytes) > 4 * 1024 * 1024:
        raise FormReadError("Image is too large - please upload a photo under 4 MB.")
    raw = reader.vision(PROMPT, base64.b64encode(image_bytes).decode(), mime)
    if not raw:
        raise FormReadError("The photo couldn't be read right now (the image model may have reached its daily "
                            "free limit). Please try again later.")
    schema = schema_from_vision_json(parse_json(raw))
    return engine.register_custom_form(schema)
