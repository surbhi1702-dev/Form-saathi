"""Session service: the only layer the API talks to.

Privacy by design:
  - sessions live only in memory (LangGraph checkpointer) and expire after SESSION_TTL_MINUTES idle
  - DELETE /sessions/{id} wipes a session immediately
  - Aadhaar / PAN / account numbers are masked in every API response; only the PDF
    the user downloads for themselves contains full values (and can be masked too)
  - user messages are never logged
"""
from __future__ import annotations

import threading
import time
import uuid

from . import i18n
from . import metrics
from .agents import nodes
from .agents.graph import build_graph
from .config import get_settings
from .forms import engine
from .i18n import loc
from .pdf.generator import build_pdf
from .validators import format_inr, shown_value

MAX_MESSAGE_CHARS = 1000
INPUT_MODES = {"text", "voice", "tap"}


class SessionNotFound(Exception):
    pass


class FormNotFound(Exception):
    pass


class SessionManager:
    def __init__(self):
        self.graph = build_graph()
        self.meta: dict[str, dict] = {}
        self.lock = threading.Lock()

    # ---------------------------------------------------------------- lifecycle
    def _config(self, sid: str) -> dict:
        return {"configurable": {"thread_id": sid}}

    def _touch(self, sid: str) -> None:
        self.purge_expired()
        if sid not in self.meta:
            raise SessionNotFound(sid)
        self.meta[sid]["last"] = time.time()

    def purge_expired(self) -> None:
        ttl = get_settings().session_ttl_minutes * 60
        now = time.time()
        for sid in [s for s, m in self.meta.items() if now - m["last"] > ttl]:
            self.delete(sid)

    def _write_metrics(self, sid: str, completed: bool) -> None:
        m = self.meta.get(sid, {}).get("metrics")
        if not m or m.get("written"):
            return
        st = self._state(sid)
        form = engine.get_form(st.get("form_id") or "")
        m["form_id"] = st.get("form_id")
        answered, total = engine.progress(form, st.get("values", {}), st.get("skipped", [])) if form else (0, 0)
        metrics.finish(m, completed=completed, fields_answered=answered, fields_total=total)

    def delete(self, sid: str) -> None:
        if sid in self.meta:
            self._write_metrics(sid, completed=False)  # no-op if already recorded as completed
        self.meta.pop(sid, None)
        saver = getattr(self.graph, "checkpointer", None)
        if saver is not None and hasattr(saver, "delete_thread"):
            saver.delete_thread(sid)

    # ---------------------------------------------------------------- turns
    def start(self, form_id: str | None, lang: str) -> dict:
        lang = lang if lang in i18n.LANGS else "en"
        if form_id and not engine.get_form(form_id):
            raise FormNotFound(form_id)
        sid = uuid.uuid4().hex
        with self.lock:
            self.meta[sid] = {"last": time.time(), "labels": {}, "metrics": metrics.new_session(form_id, lang)}
            self.graph.invoke({
                "form_id": form_id, "lang": lang, "stage": "filling" if form_id else "pick_form",
                "values": {}, "skipped": [], "history": [], "tcache": {}, "notes": {}, "current_field": None,
                "user_message": "__start__", "reply_parts": (
                    [i18n.msg("welcome", lang, form=loc(engine.get_form(form_id)["title"], lang))] if form_id else []),
                "error": None, "intent": None, "sources": [], "target_field": None,
            }, self._config(sid))
        return self.view(sid)

    def send(self, sid: str, text: str, via: str = "text") -> dict:
        self._touch(sid)
        text = (text or "").strip()[:MAX_MESSAGE_CHARS]
        if not text:
            return self.view(sid)
        with self.lock:
            t0 = time.perf_counter()
            out = self.graph.invoke({"user_message": text, "reply_parts": [], "error": None, "intent": None,
                                     "sources": [], "target_field": None}, self._config(sid))
            m = self.meta[sid]["metrics"]
            metrics.record_turn(m, intent=out.get("intent"), error=out.get("error"),
                                via=via if via in INPUT_MODES else "text", ms=(time.perf_counter() - t0) * 1000)
            if out.get("stage") == "complete":
                self._write_metrics(sid, completed=True)
        return self.view(sid)

    def set_language(self, sid: str, lang: str) -> dict:
        self._touch(sid)
        if lang in i18n.LANGS:
            with self.lock:
                self.meta[sid]["metrics"]["language_changes"] += 1
                self.graph.update_state(self._config(sid), {"lang": lang})
                if self._state(sid).get("stage") == "filling":
                    # re-ask the current question in the new language
                    self.graph.invoke({"user_message": "__start__", "reply_parts": [], "error": None,
                                       "sources": []}, self._config(sid))
        return self.view(sid)

    # ---------------------------------------------------------------- read models
    def _state(self, sid: str) -> dict:
        return self.graph.get_state(self._config(sid)).values

    def view(self, sid: str) -> dict:
        self._touch(sid)
        st = self._state(sid)
        lang = st.get("lang", "en")
        form = engine.get_form(st.get("form_id") or "")
        history = st.get("history", [])
        out = {"session_id": sid, "lang": lang, "stage": st.get("stage"), "history": history,
               "reply": history[-1]["text"] if history else "", "form": None}
        if not form:
            return out
        values, skipped = st.get("values", {}), st.get("skipped", [])
        cache = dict(st.get("tcache", {}))
        labels = self._labels(sid, form, lang, cache)
        fields = []
        for f in engine.visible_fields(form, values):
            status = "filled" if f["id"] in values else "skipped" if f["id"] in skipped else \
                "current" if f["id"] == st.get("current_field") else "pending"
            value = values.get(f["id"])
            shown = None
            if value is not None:
                shown = nodes.option_display(f, value, lang, cache) if f.get("options") else shown_value(f, value)
            fields.append({"id": f["id"], "label": labels.get(f["id"], loc(f.get("label"), "en")), "status": status,
                           "value": shown, "required": f.get("required", True), "type": f.get("type")})
        cur = engine.field_by_id(form, st.get("current_field")) if st.get("stage") == "filling" else None
        current = None
        if cur:
            current = {"id": cur["id"], "type": cur.get("type"), "required": cur.get("required", True),
                       "options": [{"value": str(i), "label": nodes.option_display(cur, o, lang, cache)}
                                   for i, o in enumerate(cur.get("options") or [], 1)]}
        done, total = engine.progress(form, values, skipped)
        show_summary = st.get("stage") in {"review", "complete"}
        out.update({
            "form": {"id": form["id"], "title": loc(form["title"], lang), "department": form.get("department", ""),
                     "output": form.get("output", "form"), "category": form.get("category")},
            "progress": {"done": done, "total": total},
            "fields": fields,
            "current_field": st.get("current_field"),
            "current": current,
            "computed": [{"label": loc(c["label"], "en"), "value": engine.computed_display(c)}
                         for c in engine.compute_values(form, values)] if show_summary else [],
            "warnings": nodes.translate_many(engine.run_checks(form, values), lang, cache) if show_summary else [],
            "documents": nodes.translate_many(form.get("documents", []), lang, cache),
            "submit_note": nodes.translate(form.get("submit_note", ""), lang, cache) if show_summary else "",
            "sources": history[-1].get("sources", []) if history else [],
            "can_download": st.get("stage") in {"review", "complete"},
        })
        return out

    def _labels(self, sid: str, form: dict, lang: str, cache: dict) -> dict:
        key = f"{form['id']}::{lang}"
        stored = self.meta[sid]["labels"]
        if key not in stored:
            ids, texts = [], []
            for f in form["fields"]:
                if not i18n.has_translation(f.get("label"), lang):
                    ids.append(f["id"])
                    texts.append(loc(f.get("label"), "en"))
            translated = dict(zip(ids, nodes.translate_many(texts, lang, cache)))
            stored[key] = {f["id"]: translated.get(f["id"], loc(f.get("label"), lang)) for f in form["fields"]}
        return stored[key]

    def pdf(self, sid: str, mask_sensitive: bool = False) -> tuple[bytes, str]:
        self._touch(sid)
        st = self._state(sid)
        form = engine.get_form(st.get("form_id") or "")
        if not form:
            raise FormNotFound("no form in session")
        data = build_pdf(form, st.get("values", {}), st.get("notes", {}), mask_sensitive=mask_sensitive)
        return data, f"{form['id']}_draft.pdf"

    def guide(self, sid: str) -> dict:
        """One step per box on the paper form, with the full value to write there (in the form's own script)."""
        self._touch(sid)
        st = self._state(sid)
        form = engine.get_form(st.get("form_id") or "")
        if not form:
            raise FormNotFound("no form in session")
        lang = st.get("lang", "en")
        values, skipped = st.get("values", {}), st.get("skipped", [])
        cache = dict(st.get("tcache", {}))
        labels = self._labels(sid, form, lang, cache)
        steps = []
        for f in engine.visible_fields(form, values):
            if f["id"] not in values and f["id"] not in skipped:
                continue
            steps.append({"id": f["id"], "label": labels.get(f["id"], loc(f.get("label"), "en")),
                          "printed_label": loc(f.get("label"), "en"), "type": f.get("type"),
                          "value": paper_value(f, values[f["id"]]) if f["id"] in values else None,
                          "box": f.get("box")})
        for c in engine.compute_values(form, values):
            label = loc(c["label"], lang) if i18n.has_translation(c["label"], lang) else \
                nodes.translate(loc(c["label"], "en"), lang, cache)
            steps.append({"id": c["id"], "label": label, "printed_label": loc(c["label"], "en"),
                          "type": "computed", "box": None,
                          "value": format_inr(c["value"]) if c["kind"] == "amount" else str(c["value"])})
        return {"form": {"id": form["id"], "title": loc(form["title"], lang), "category": form.get("category")},
                "has_boxes": any(s["box"] for s in steps), "steps": steps}


def paper_value(field: dict, value) -> str:
    """What to write on paper: the full value, the printed option for tick boxes, amounts without 'Rs.'."""
    if field.get("type") == "amount" and isinstance(value, (int, float)):
        return format_inr(value)
    return str(value)


sessions = SessionManager()
