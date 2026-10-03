"""Day 3 Example 3: Checkpoint 断点续跑

目标:
    1. 学会 MemorySaver 用法
    2. 学会 thread_id 标识会话
    3. 看到 state 跨 invoke 持久化(分两次调用也能续上)

核心概念:
    - checkpointer:LangGraph 的 state 持久化机制
      (内存版 = MemorySaver,生产版 = SqliteSaver/PostgresSaver)
    - thread_id:会话标识,同一个 thread_id 才能续上

应用场景:
    - 浏览器任务跑一半程序崩了?重启后从同一 thread_id 续跑
    - 长任务想暂停改 prompt?用 interrupt + thread_id 续跑
    - 多用户:每个用户一个 thread_id,state 互不干扰
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph


class CounterState(TypedDict):
    counter: int
    log: list[str]


def increment(state: CounterState) -> dict:
    new_count = state["counter"] + 1
    return {"counter": new_count, "log": state["log"] + [f"step {new_count}"]}


def should_continue(state: CounterState) -> Literal["increment", "__end__"]:
    if state["counter"] < 3:  # 改为 3 步,方便看续跑
        return "increment"
    return END


def build_graph_with_checkpoint() -> StateGraph:
    """带 checkpointer 的图。"""
    workflow = StateGraph(CounterState)
    workflow.add_node("increment", increment)
    workflow.add_edge(START, "increment")
    workflow.add_conditional_edges("increment", should_continue)

    # 关键:挂上 checkpointer
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def main() -> None:
    print("=== LangGraph Example 3: Checkpoint 断点续跑 ===")
    app = build_graph_with_checkpoint()

    # thread_id 决定"哪个会话"
    config = {"configurable": {"thread_id": "demo-thread-1"}}

    # 第一次:只跑 1 步(counter=0 -> 1),然后"假装程序挂了"
    print("\n[第 1 次 invoke] 模拟跑到一半程序崩了:")
    for chunk in app.stream({"counter": 0, "log": []}, config=config):
        print(f"  chunk: {chunk}")
        # 实际场景:第 N 步后 crash。这里我们在 counter=1 时 break。
        snapshot = app.get_state(config)
        if snapshot.values["counter"] >= 1:
            print("  [模拟崩溃] 强行中断")
            break

    # 重新启动后,从同一 thread_id 读取 state
    print("\n[重启后] 读取 checkpoint state:")
    snapshot = app.get_state(config)
    print(f"  thread_id={config['configurable']['thread_id']}")
    print(f"  恢复的 counter: {snapshot.values['counter']}")
    print(f"  恢复的 log: {snapshot.values['log']}")

    # 第二次:从 checkpoint 续跑(不传初始值也行,因为有 checkpointer)
    print("\n[第 2 次 invoke] 续跑(不传 initial):")
    for chunk in app.stream(None, config=config):
        print(f"  chunk: {chunk}")

    final = app.get_state(config).values
    print(f"\n最终 state: counter={final['counter']}, log={final['log']}")


if __name__ == "__main__":
    main()
