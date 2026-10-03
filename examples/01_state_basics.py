"""Day 3 Example 1: LangGraph 基础 — State / Node / Edge

目标:
    1. 理解 StateGraph 的最小骨架
    2. 学会 TypedDict 定义状态 schema
    3. 学会 add_node / add_edge / compile / invoke

核心概念:
    - State:全局状态(类型为 TypedDict),在节点间流转
    - Node:一个函数,接收 state 返回 state 的子集(增量更新)
    - Edge:节点之间的固定连接(START → node → ... → END)

最小 LangGraph 程序 = 1 个 state + 1 个 node + 1 条边
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class CounterState(TypedDict):
    """计数器状态:每一步 +1 并记录日志。"""

    counter: int
    log: list[str]


def increment(state: CounterState) -> dict:
    """节点函数:接收 state,返回要更新的字段(增量)。"""
    new_count = state["counter"] + 1
    new_log = state["log"] + [f"step {new_count}"]
    print(f"  [increment] counter: {state['counter']} -> {new_count}")
    return {"counter": new_count, "log": new_log}


def build_graph() -> StateGraph:
    """构建一个最简图:START -> increment -> END。"""
    workflow = StateGraph(CounterState)
    workflow.add_node("increment", increment)
    workflow.add_edge(START, "increment")
    workflow.add_edge("increment", END)
    return workflow.compile()


def main() -> None:
    print("=== LangGraph Example 1: 最小状态机 ===")
    app = build_graph()

    # 初始 state
    initial: CounterState = {"counter": 0, "log": []}
    print(f"初始 state: {initial}")

    # 跑一次 — 因为只有一条边,只执行一次 increment
    result = app.invoke(initial)
    print(f"最终 state: {result}")


if __name__ == "__main__":
    main()
