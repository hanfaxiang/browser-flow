"""Day 4 测试 2: Browser-Use 节点在 LangGraph 集成

不跑真实浏览器、不调 LLM,只测 LangGraph 编排是否正确。

策略:
    1. 定义一个最小 LangGraph,节点函数被 monkeypatch 替换成 mock
    2. mock 返回假 history,断言 LangGraph 能正确 merge state
    3. 测试端到端 invoke 后的 state 字段被填充

这覆盖了关键的"装配逻辑",不依赖任何网络/浏览器/LLM。
"""

from __future__ import annotations

from typing import Any, TypedDict
from unittest.mock import MagicMock

import pytest
from langgraph.graph import END, START, StateGraph


class _BrowserState(TypedDict):
    task: str
    result: str
    success: bool


def _build_graph_with_node(node_fn):
    workflow = StateGraph(_BrowserState)
    workflow.add_node("browser", node_fn)
    workflow.add_edge(START, "browser")
    workflow.add_edge("browser", END)
    return workflow.compile()


def test_node_returns_correct_dict_keys() -> None:
    """节点函数返回 dict 含 result / success 两个字段。"""

    def fake_run_browser_agent(state: _BrowserState) -> dict:
        return {"result": f"fake result for {state['task']}", "success": True}

    app = _build_graph_with_node(fake_run_browser_agent)
    final = app.invoke({"task": "test", "result": "", "success": False})

    assert final["result"] == "fake result for test"
    assert final["success"] is True


def test_node_called_with_state() -> None:
    """节点函数应该被 LangGraph 用 state 调用。"""
    called_with: list[_BrowserState] = []

    def recording_node(state: _BrowserState) -> dict:
        called_with.append(state)
        return {"result": "ok", "success": True}

    app = _build_graph_with_node(recording_node)
    initial = {"task": "verify-me", "result": "", "success": False}
    app.invoke(initial)

    assert len(called_with) == 1
    assert called_with[0]["task"] == "verify-me"


def test_browser_use_agent_mock_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """端到端:mock Agent.run_sync + __init__ 后,LangGraph 能完整跑完并填充 state。"""
    fake_history = MagicMock()
    fake_history.final_result.return_value = "抓到了 5 条名言"

    from browser_use import Agent as RealAgent

    # 完全跳过 Agent.__init__ 内部的 LLM 验证(否则 llm=None 会要 BROWSER_USE_API_KEY)
    def fake_agent_init(self: Any, task: str, llm: Any = None, **kwargs: Any) -> None:
        self.task = task
        self.llm = llm

    monkeypatch.setattr(RealAgent, "__init__", fake_agent_init)
    monkeypatch.setattr(RealAgent, "run_sync", MagicMock(return_value=fake_history))

    def browser_node(state: _BrowserState) -> dict:
        agent = RealAgent(task=state["task"], llm=MagicMock())
        history = agent.run_sync(max_steps=1)
        final = history.final_result()
        return {"result": str(final), "success": bool(final)}

    app = _build_graph_with_node(browser_node)
    initial = {"task": "real agent but mocked run_sync", "result": "", "success": False}
    final = app.invoke(initial)

    assert final["result"] == "抓到了 5 条名言"
    assert final["success"] is True
    assert final["task"] == "real agent but mocked run_sync"


def test_node_failure_propagates_to_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """节点跑失败时(final_result=None),state 的 success 应为 False。"""
    from browser_use import Agent as RealAgent

    fake_history = MagicMock()
    fake_history.final_result.return_value = None  # 没抓到数据

    def fake_agent_init(self: Any, task: str, llm: Any = None, **kwargs: Any) -> None:
        self.task = task
        self.llm = llm

    monkeypatch.setattr(RealAgent, "__init__", fake_agent_init)
    monkeypatch.setattr(RealAgent, "run_sync", MagicMock(return_value=fake_history))

    def browser_node(state: _BrowserState) -> dict:
        agent = RealAgent(task=state["task"], llm=MagicMock())
        history = agent.run_sync(max_steps=1)
        final = history.final_result()
        return {"result": "" if not final else str(final), "success": bool(final)}

    app = _build_graph_with_node(browser_node)
    final = app.invoke({"task": "test empty", "result": "", "success": False})

    assert final["success"] is False
    assert final["result"] == ""
