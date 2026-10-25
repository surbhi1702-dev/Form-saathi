"""FastAPI app. Run:  uvicorn app.main:app --reload --port 8000  (from the backend/ folder)."""
from __future__ import annotations

import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from . import i18n, metrics
from .agents.graph import USING_LANGGRAPH
from .agents.vision import FormReadError, read_form_image
from .config import get_settings
from .forms import engine
from .i18n import loc
from .llm import get_llm, get_vision
from .service import FormNotFound, SessionNotFound, sessions

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
settings = get_settings()

app = FastAPI(title="Form Saathi API", version="1.0.0",
              description="Multilingual, multi-agent assistant that helps people fill Indian forms.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])


class StartRequest(BaseModel):
    form_id: str | None = None
    lang: str = "en"


class MessageRequest(BaseModel):
    text: str = Field(..., max_length=1000)
    via: str = "text"  # text | voice | tap - used only for anonymous usage counts


class LanguageRequest(BaseModel):
    lang: str


def _form_card(form: dict, lang: str) -> dict:
    return {"id": form["id"], "category": form.get("category"), "title": loc(form["title"], lang),
            "description": loc(form.get("description", ""), lang), "department": form.get("department", ""),
            "question_count": len(form["fields"])}


@app.get("/api/health")
def health():
    llm = get_llm()
    reader = get_vision() if not llm.is_mock else None
    out = {"ok": True, "llm": "mock" if llm.is_mock else "groq", "langgraph": USING_LANGGRAPH,
           "forms": len(engine.all_forms()), "photo_reading": reader is not None}
    if not llm.is_mock:
        out.update(chat_model=llm.chat_model, vision_model=getattr(reader, "vision_model", None),
                   vision_provider=getattr(reader, "provider", None),
                   model_warnings=llm.models["warnings"],
                   models_available_to_key=llm.models["available"])
    return out


@app.get("/api/metrics")
def usage_metrics():
    """Anonymous usage summary (counts only - no answers or personal details are stored)."""
    from .llm import STATS

    lat = sorted(STATS["latencies_ms"])
    return {**metrics.summarize(metrics.load_records()),
            "llm_calls_since_start": STATS["calls"], "llm_errors_since_start": STATS["errors"],
            "llm_median_call_ms": lat[len(lat) // 2] if lat else None}


@app.get("/api/forms")
def list_forms(lang: str = "en", q: str | None = None):
    forms = engine.all_forms()
    if q:
        ranked = [fid for fid, _ in engine.match_forms(q, limit=5)]
        return {"forms": [_form_card(forms[f], lang) for f in ranked]}
    cards = [_form_card(f, lang) for f in forms.values() if f.get("category") != "custom"]
    order = {c: i for i, c in enumerate(engine.CATEGORIES)}
    return {"forms": sorted(cards, key=lambda c: (order.get(c["category"], 99), c["title"]))}


@app.get("/api/forms/{form_id}")
def form_detail(form_id: str, lang: str = "en"):
    form = engine.get_form(form_id)
    if not form:
        raise HTTPException(404, "Form not found")
    return {**_form_card(form, lang), "documents": form.get("documents", []), "submit_note": form.get("submit_note", ""),
            "fields": [{"id": f["id"], "label": loc(f.get("label"), lang), "type": f["type"],
                        "required": f.get("required", True)} for f in form["fields"]]}


@app.post("/api/forms/scan")
async def scan_form(image: UploadFile = File(...)):
    data = await image.read()
    try:
        form = read_form_image(data, image.content_type or "")
    except FormReadError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _form_card(form, "en")


@app.post("/api/sessions")
def start_session(req: StartRequest):
    try:
        return sessions.start(req.form_id, req.lang if req.lang in i18n.LANGS else "en")
    except FormNotFound as exc:
        raise HTTPException(404, "Form not found") from exc


@app.get("/api/sessions/{sid}")
def get_session(sid: str):
    try:
        return sessions.view(sid)
    except SessionNotFound as exc:
        raise HTTPException(404, "Session expired or not found") from exc


@app.post("/api/sessions/{sid}/messages")
def send_message(sid: str, req: MessageRequest):
    try:
        return sessions.send(sid, req.text, req.via)
    except SessionNotFound as exc:
        raise HTTPException(404, "Session expired or not found") from exc


@app.post("/api/sessions/{sid}/language")
def change_language(sid: str, req: LanguageRequest):
    try:
        return sessions.set_language(sid, req.lang)
    except SessionNotFound as exc:
        raise HTTPException(404, "Session expired or not found") from exc


@app.get("/api/sessions/{sid}/pdf")
def download_pdf(sid: str, mask: bool = False):
    try:
        data, filename = sessions.pdf(sid, mask_sensitive=mask)
    except SessionNotFound as exc:
        raise HTTPException(404, "Session expired or not found") from exc
    except FormNotFound as exc:
        raise HTTPException(400, "Pick a form first") from exc
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})


@app.get("/api/sessions/{sid}/guide")
def guide(sid: str):
    """Box-by-box steps for copying the answers onto the paper form. Full values, like the PDF - never cached."""
    try:
        data = sessions.guide(sid)
    except SessionNotFound as exc:
        raise HTTPException(404, "Session expired or not found") from exc
    except FormNotFound as exc:
        raise HTTPException(400, "Pick a form first") from exc
    return JSONResponse(data, headers={"Cache-Control": "no-store"})


@app.delete("/api/sessions/{sid}")
def delete_session(sid: str):
    sessions.delete(sid)
    return {"deleted": True}
