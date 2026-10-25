"""A tiny, dependency-free stand-in for LangGraph's StateGraph.

The app always prefers real LangGraph (see graph.py). This fallback exists so the
agent graph can be unit-tested in environments where langgraph isn't installed.
It implements only what Form Saathi uses: nodes, edges, conditional edges from
START or any node, a per-thread in-memory checkpointer, invoke() and get_state().
"""
from __future__ import annotations

import copy
from types import SimpleNamespace

START = "__start__"
END = "__end__"


class MemorySaver:
    def __init__(self):
        self.storage: dict[str, dict] = {}

    def delete_thread(self, thread_id: str) -> None:
        self.storage.pop(thread_id, None)


class _Compiled:
    def __init__(self, nodes, edges, cond, checkpointer, recursion_limit=25):
        self.nodes, self.edges, self.cond = nodes, edges, cond
        self.checkpointer = checkpointer or MemorySaver()
        self.recursion_limit = recursion_limit

    def _next(self, current: str, state: dict) -> str:
        if current in self.cond:
            fn, mapping = self.cond[current]
            key = fn(state)
            return mapping[key] if mapping else key
        return self.edges.get(current, END)

    def invoke(self, inputs: dict, config: dict | None = None) -> dict:
        thread = (config or {}).get("configurable", {}).get("thread_id", "default")
        state = copy.deepcopy(self.checkpointer.storage.get(thread, {}))
        state.update(copy.deepcopy(inputs))
        node, steps = self._next(START, state), 0
        while node != END:
            steps += 1
            if steps > self.recursion_limit:
                raise RecursionError("Graph recursion limit reached")
            update = self.nodes[node](state) or {}
            state.update(update)
            node = self._next(node, state)
        self.checkpointer.storage[thread] = copy.deepcopy(state)
        return state

    def update_state(self, config: dict, values: dict) -> None:
        thread = config.get("configurable", {}).get("thread_id", "default")
        self.checkpointer.storage.setdefault(thread, {}).update(copy.deepcopy(values))

    def get_state(self, config: dict):
        thread = config.get("configurable", {}).get("thread_id", "default")
        return SimpleNamespace(values=copy.deepcopy(self.checkpointer.storage.get(thread, {})))


class StateGraph:
    def __init__(self, _state_type=None):
        self.nodes, self.edges, self.cond = {}, {}, {}

    def add_node(self, name, fn):
        self.nodes[name] = fn

    def add_edge(self, src, dst):
        self.edges[src] = dst

    def add_conditional_edges(self, src, fn, mapping=None):
        self.cond[src] = (fn, mapping)

    def compile(self, checkpointer=None):
        return _Compiled(self.nodes, self.edges, self.cond, checkpointer)
