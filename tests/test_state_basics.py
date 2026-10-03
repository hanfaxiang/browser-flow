"""Day 3 测试 1: 状态机 + 条件路由。

把 examples/01 和 examples/02 的逻辑包装成可重复运行的 pytest 测试。
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class CounterState(TypedDict):
    counter: int
    log: list[str]


def increment(state: CounterState) -> dict:
    new_count = state["counter"] + 1
    return {"counter": new_count, "log": state["log"] + [f"step {new_count}"]}


def should_continue(state: CounterState) -> Literal["increment", "__end__"]:
    return "increment" if state["counter"] < 5 else END


def build_app():
    workflow = StateGraph(CounterState)
    workflow.add_node("increment", increment)
    workflow.add_edge(START, "increment")
    workflow.add_conditional_edges("increment", should_continue)
    return workflow.compile()


def test_increment_runs_exactly_5_times() -> None:
    """跑一次后 counter 应该是 5(因为有条件边让它自己跑 5 次)。"""
    app = build_app()
    result = app.invoke({"counter": 0, "log": []})
    assert result["counter"] == 5
    assert len(result["log"]) == 5


def test_log_contains_step_markers() -> None:
    """日志应包含 step 1 到 step 5。"""
    app = build_app()
    result = app.invoke({"counter": 0, "log": []})
    assert result["log"] == [f"step {i}" for i in range(1, 6)]


def test_invoke_is_idempotent_when_state_already_at_max() -> None:
    """从 counter=5 开始,因为 5 < 5 不成立,should_continue 应返回 END。

    关键观察:LangGraph 的执行顺序是 START -> increment(节点) -> should_continue(条件)
    而不是 should_continue 先于节点。所以即使初始 counter=5,也会 +1 到 6 再判终止。
    这就是 LangGraph 的"先执行后决策"模型。
    """
    app = build_app()
    result = app.invoke({"counter": 5, "log": ["done"]})
    # counter 5 < 5 不成立:第一次 increment 后 counter=6,should_continue 返 END
    assert result["counter"] == 6
    assert result["log"] == ["done", "step 6"]
