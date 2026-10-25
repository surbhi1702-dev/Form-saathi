"""Shared LangGraph state. Kept JSON-serialisable so any LangGraph checkpointer can persist it."""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class FormState(TypedDict, total=False):
    # session-level (persisted across turns by the checkpointer)
    form_id: Optional[str]
    lang: str                       # en | ta | hi | or
    stage: str                      # pick_form | filling | review | complete
    values: dict[str, Any]          # field_id -> normalised value
    skipped: list[str]              # optional fields the user skipped
    current_field: Optional[str]    # field currently being asked
    history: list[dict]             # [{role, text}] chat transcript
    tcache: dict[str, str]          # translation cache "lang::text" -> translated
    notes: dict[str, str]           # per-field notes (e.g. how a load estimate was computed)

    # turn-level (reset by the service on every message)
    user_message: str
    intent: Optional[str]           # answer | explain | skip | correct | confirm | info
    target_field: Optional[str]
    error: Optional[str]
    reply_parts: list[str]
    reply: str
    sources: list[str]
