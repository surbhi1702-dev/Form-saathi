"""Wires the agents into a LangGraph StateGraph.

                      ┌────────────► intake ──(form found)──► ask ─┐
 START ─► route ──────┼─ "__start__" ─────────────────────► ask ─┤
                      └────────────► classify                     │
                                       │ answer  ─► extract_validate ─ ok ─► advance ─► ask / review
                                       │                          └─ bad ─► reask
                                       │ explain ─► explain (RAG)
                                       │ skip    ─► skip ─► advance (or ask again if required)
                                       │ correct ─► correct ─► ask
                                       │ confirm ─► finish
                                       └ info    ─► info
 every path ends in respond ─► END   (respond writes the reply + chat history)

One graph invocation = one user message. The checkpointer keeps per-session state
between messages, keyed by thread_id = session id.
"""
from __future__ import annotations

from ..forms import engine
from . import nodes
from .state import FormState

try:  # real LangGraph (pip install langgraph)
    from langgraph.graph import END, START, StateGraph
    try:
        from langgraph.checkpoint.memory import InMemorySaver as MemorySaver
    except ImportError:  # older langgraph
        from langgraph.checkpoint.memory import MemorySaver
    USING_LANGGRAPH = True
except ImportError:  # test fallback - same API subset
    from .mini_graph import END, START, MemorySaver, StateGraph
    USING_LANGGRAPH = False


def route_entry(state: FormState) -> str:
    if state.get("user_message") == "__start__":
        return "ask" if state.get("form_id") else "intake"
    if not state.get("form_id") or state.get("stage") == "pick_form":
        return "intake"
    return "classify"


def route_intent(state: FormState) -> str:
    return {"answer": "extract_validate", "explain": "explain", "skip": "skip", "correct": "correct",
            "confirm": "finish", "info": "info"}.get(state.get("intent") or "answer", "extract_validate")


def route_after_extract(state: FormState) -> str:
    return "reask" if state.get("error") else "advance"


def route_after_skip(state: FormState) -> str:
    return "ask" if state.get("error") == "cannot_skip" else "advance"


def route_after_intake(state: FormState) -> str:
    return "ask" if state.get("form_id") and state.get("stage") == "filling" else "respond"


def route_after_correct(state: FormState) -> str:
    return "ask" if state.get("target_field") else "respond"


def route_advance(state: FormState) -> str:
    form = engine.get_form(state.get("form_id") or "")
    nxt = engine.next_field(form, state.get("values", {}), state.get("skipped", []))
    return "ask" if nxt else "review"


def _advance(state: FormState) -> dict:
    return {}


def build_graph(checkpointer=None):
    g = StateGraph(FormState)
    for name, fn in [("intake", nodes.intake), ("classify", nodes.classify),
                     ("extract_validate", nodes.extract_validate), ("reask", nodes.reask),
                     ("explain", nodes.explain), ("skip", nodes.skip), ("correct", nodes.correct),
                     ("advance", _advance), ("ask", nodes.ask), ("review", nodes.review),
                     ("finish", nodes.finish), ("info", nodes.info), ("respond", nodes.respond)]:
        g.add_node(name, fn)

    g.add_conditional_edges(START, route_entry, {"intake": "intake", "ask": "ask", "classify": "classify"})
    g.add_conditional_edges("intake", route_after_intake, {"ask": "ask", "respond": "respond"})
    g.add_conditional_edges("classify", route_intent, {
        "extract_validate": "extract_validate", "explain": "explain", "skip": "skip",
        "correct": "correct", "finish": "finish", "info": "info"})
    g.add_conditional_edges("extract_validate", route_after_extract, {"reask": "reask", "advance": "advance"})
    g.add_conditional_edges("skip", route_after_skip, {"ask": "ask", "advance": "advance"})
    g.add_conditional_edges("correct", route_after_correct, {"ask": "ask", "respond": "respond"})
    g.add_conditional_edges("advance", route_advance, {"ask": "ask", "review": "review"})
    for name in ["reask", "explain", "ask", "review", "finish", "info"]:
        g.add_edge(name, "respond")
    g.add_edge("respond", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())
