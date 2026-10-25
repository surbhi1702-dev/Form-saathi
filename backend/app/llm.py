"""LLM access layer.

GroqLLM   - real model, called through a LangChain chain (prompt | ChatGroq | parser).
            Falls back to Groq's OpenAI-compatible HTTP API if LangChain isn't installed.
MockLLM   - offline stand-in that returns "" so every agent uses its deterministic path.
            Used in tests and when GROQ_API_KEY is not set, so the app always works.

Every agent treats an empty / unparseable answer as "LLM unavailable" and falls back
to rule-based logic. A Groq outage therefore degrades quality instead of crashing.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from typing import Any

from .config import Settings, get_settings

log = logging.getLogger("formsaathi.llm")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Simple counters so the eval script and /api/metrics can report LLM usage and latency.
STATS: dict[str, Any] = {"calls": 0, "errors": 0, "latencies_ms": []}
_stats_lock = threading.Lock()


def _record(ms: float, ok: bool) -> None:
    with _stats_lock:
        STATS["calls"] += 1
        if not ok:
            STATS["errors"] += 1
        STATS["latencies_ms"].append(round(ms, 1))
        del STATS["latencies_ms"][:-2000]  # keep the last 2000 only


def reset_stats() -> None:
    with _stats_lock:
        STATS.update(calls=0, errors=0, latencies_ms=[])


def _strip_thinking(text: str) -> str:
    """Some reasoning models put their thinking in <think>...</think> before the answer."""
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()


class _Throttle:
    """Keeps calls under LLM_MAX_RPM requests per minute (Groq's free tier has per-minute limits)."""

    def __init__(self):
        self.times: list[float] = []
        self.lock = threading.Lock()

    def wait(self) -> None:
        rpm = int(os.getenv("LLM_MAX_RPM", "0") or 0)
        if rpm <= 0:
            return
        with self.lock:
            now = time.monotonic()
            self.times = [t for t in self.times if now - t < 60]
            if len(self.times) >= rpm:
                time.sleep(60 - (now - self.times[0]) + 0.05)
            self.times.append(time.monotonic())


_throttle = _Throttle()


class MockLLM:
    is_mock = True

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:  # noqa: ARG002
        return ""

    def vision(self, prompt: str, image_b64: str, mime: str) -> str:  # noqa: ARG002
        return ""


# Tried in order when the configured model isn't available to this API key.
# Groq adds and retires models over time - check https://console.groq.com/docs/models
CHAT_FALLBACKS = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3.8-27b",
                  "openai/gpt-oss-20b", "llama-3.1-8b-instant"]
VISION_FALLBACKS = ["meta-llama/llama-4-scout-17b-16e-instruct", "meta-llama/llama-4-maverick-17b-128e-instruct"]
VISION_HINTS = ("vision", "scout", "maverick", "-vl", "llava")


def available_models(api_key: str) -> list[str] | None:
    """Model IDs this key can use, from Groq's /models endpoint. None if the list couldn't be fetched."""
    try:
        import requests

        r = requests.get("https://api.groq.com/openai/v1/models",
                         headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
        r.raise_for_status()
        return sorted(m["id"] for m in r.json().get("data", []) if m.get("active", True))
    except Exception as exc:
        log.warning("Couldn't list Groq models: %s", exc)
        return None


def pick_models(configured_chat: str, configured_vision: str, available: list[str] | None) -> dict:
    """Keep the configured models when available; otherwise fall back and explain why."""
    info = {"available": available, "warnings": []}
    if available is None:  # can't check - trust the configuration
        info.update(chat=configured_chat, vision=configured_vision)
        return info
    chat = next((m for m in [configured_chat, *CHAT_FALLBACKS] if m in available), None)
    if chat is None:
        chat = next((m for m in available if not any(x in m for x in ("whisper", "guard", "orpheus", "tts"))), None)
    if chat != configured_chat:
        info["warnings"].append(f"Chat model '{configured_chat}' isn't available to this API key; using '{chat}'.")
    vision = next((m for m in [configured_vision, *VISION_FALLBACKS] if m in available), None)
    if vision is None:
        vision = next((m for m in available if any(h in m for h in VISION_HINTS)), None)
    if vision != configured_vision:
        info["warnings"].append(
            f"Vision model '{configured_vision}' isn't available; "
            + (f"using '{vision}'." if vision else "reading forms from photos is turned off."))
    info.update(chat=chat, vision=vision)
    return info


class GroqLLM:
    is_mock = False

    def __init__(self, settings: Settings):
        self.settings = settings
        self._chain = None
        self.models = pick_models(settings.chat_model, settings.vision_model, available_models(settings.groq_api_key))
        for w in self.models["warnings"]:
            log.warning(w)
        self.chat_model = self.models["chat"] or settings.chat_model
        self.vision_model = self.models["vision"]
        try:  # Preferred path: LangChain
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_groq import ChatGroq

            self._lc_model = ChatGroq(
                model=self.chat_model, api_key=settings.groq_api_key, temperature=0.2, max_retries=2
            )
            prompt = ChatPromptTemplate.from_messages([("system", "{system}"), ("human", "{user}")])
            self._chain = prompt | self._lc_model | StrOutputParser()
        except ImportError:
            log.warning("langchain-groq not installed; using direct HTTP calls to Groq")

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        _throttle.wait()
        t0 = time.perf_counter()
        try:
            if self._chain is not None:
                out = self._chain.invoke({"system": system, "user": user}).strip()
            else:
                out = self._http([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                 self.chat_model, temperature)
            _record((time.perf_counter() - t0) * 1000, True)
            return _strip_thinking(out)
        except Exception as exc:  # network / rate limit / model retired
            _record((time.perf_counter() - t0) * 1000, False)
            log.warning("LLM call failed, falling back to rules: %s", exc)
            return ""

    def vision(self, prompt: str, image_b64: str, mime: str) -> str:
        if not self.vision_model:
            log.warning("No vision model available to this API key")
            return ""
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
        ]
        _throttle.wait()
        t0 = time.perf_counter()
        try:
            try:
                from langchain_core.messages import HumanMessage
                from langchain_groq import ChatGroq

                model = ChatGroq(model=self.vision_model, api_key=self.settings.groq_api_key,
                                 temperature=0.0)
                out = str(model.invoke([HumanMessage(content=content)]).content).strip()
            except ImportError:
                out = self._http([{"role": "user", "content": content}], self.vision_model, 0.0)
            _record((time.perf_counter() - t0) * 1000, True)
            return out
        except Exception as exc:
            _record((time.perf_counter() - t0) * 1000, False)
            log.warning("Vision call failed: %s", exc)
            return ""

    def _http(self, messages: list[dict], model: str, temperature: float) -> str:
        import requests

        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {self.settings.groq_api_key}"},
            json={"model": model, "messages": messages, "temperature": temperature},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


_llm_singleton: Any = None


def get_llm():
    global _llm_singleton
    settings = get_settings()
    if _llm_singleton is None or getattr(_llm_singleton, "is_mock", True) != settings.use_mock:
        _llm_singleton = MockLLM() if settings.use_mock else GroqLLM(settings)
    return _llm_singleton


def set_llm(llm) -> None:
    """Test hook: inject a fake LLM."""
    global _llm_singleton
    _llm_singleton = llm


def parse_json(text: str) -> Any | None:
    """Pull the first JSON object/array out of an LLM reply (models sometimes wrap it in prose)."""
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    for candidate in (text, *re.findall(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)):
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def chat_json(system: str, user: str) -> Any | None:
    llm = get_llm()
    if llm.is_mock:
        return None
    return parse_json(llm.chat(system + "\nReply with JSON only.", user, temperature=0.0))
