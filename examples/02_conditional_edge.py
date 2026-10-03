"""Day 3 Example 2: 条件路由 — 让图自己决定下一步去哪

目标:
    1. 学会 add_conditional_edges 用法
    2. 学会定义路由函数(返回下一个节点的 name 或 END)
    3. 看到 LangGraph 的循环结构

核心概念:
    - 条件边:不是固定的"increment -> END",而是"increment -> 根据 state 选下一步"
    - 路由函数:必须返回字面量字符串(下一个节点的 name)

应用场景:
    - 浏览器任务:"还在跑?继续": END;"还有子任务?下一个子任务": "browser";"出错?": "error_handler"
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
    """路由函数:counter < 5 就继续,否则结束。

    返回类型必须是 Literal,把"可能去的所有节点名"列出来。
    实际字符串可以是节点名(去节点)或 END(结束)。
    """
    if state["counter"] < 5:
        return "increment"
    return END  # END 是特殊字符串常量,等价于 "__end__"


def build_graph() -> StateGraph:
    workflow = StateGraph(CounterState)
    workflow.add_node("increment", increment)

    workflow.add_edge(START, "increment")
    # 条件边:increment 节点 -> 路由函数 -> "increment"(自己)或 END
    workflow.add_conditional_edges("increment", should_continue)

    return workflow.compile()


def main() -> None:
    print("=== LangGraph Example 2: 条件路由(5 步累加) ===")
    app = build_graph()

    result = app.invoke({"counter": 0, "log": []})

    print(f"最终 counter: {result['counter']}")
    print("执行轨迹:")
    for entry in result["log"]:
        print(f"  - {entry}")


if __name__ == "__main__":
    main()
