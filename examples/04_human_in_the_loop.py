"""Day 3 Example 4: Human-in-the-Loop(人工介入)

目标:
    1. 学会 interrupt 函数挂起
    2. 学会 Command(resume=...) 恢复并传参
    3. 看到图在等待人工时停在某个节点不动

核心概念:
    - interrupt():让图"暂停",等下次 invoke(Command(resume=...)) 时,
      函数返回的就是 resume 的值。
    - Command:LangGraph v1 的恢复 API。
      传 resume=... 等于"你刚才问的问题答案是 X"。

应用场景:
    - 浏览器要登录?interrupt 暂停等用户扫码
    - 遇到验证码?interrupt 让人填
    - 涉及敏感操作(转账、删除)前?interrupt 让人确认
    - 抓数据前让人选择抓哪些字段
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class BrowserTaskState(TypedDict):
    """模拟一个浏览器任务:抓数据前需要人确认。"""

    user_goal: str
    confirmed: bool
    user_reply: str
    extracted_data: str


def ask_human(state: BrowserTaskState) -> dict:
    """第一个节点:问用户是否要继续抓数据。

    interrupt() 会让图暂停,直到外部用 Command(resume=...) 恢复。
    """
    print(f"  [ask_human] 准备执行目标: {state['user_goal']}")
    print("  [ask_human] 正在等待人工确认 ...")

    # interrupt 会暂停图,返回值是外面 resume 进来的值
    user_reply = interrupt("请输入 ok 确认,或者 cancel 取消:")

    # 模拟根据 user_reply 决定 confirmed
    confirmed = user_reply.strip().lower() == "ok"
    print(f"  [ask_human] 收到回答: {user_reply!r} -> confirmed={confirmed}")
    return {"confirmed": confirmed, "user_reply": user_reply}


def extract_data(state: BrowserTaskState) -> dict:
    """第二个节点:抓数据(模拟)。"""
    if not state["confirmed"]:
        return {"extracted_data": "(用户取消,未抓取)"}
    return {"extracted_data": f"已为 {state['user_goal']!r} 抓取 42 条数据"}


def route_after_confirm(state: BrowserTaskState) -> str:
    """根据 confirmed 决定下一步。"""
    return "extract_data" if state["confirmed"] else END


def build_graph() -> StateGraph:
    workflow = StateGraph(BrowserTaskState)
    workflow.add_node("ask_human", ask_human)
    workflow.add_node("extract_data", extract_data)

    workflow.add_edge(START, "ask_human")
    # ask_human 后根据 confirmed 决定
    workflow.add_conditional_edges("ask_human", route_after_confirm)
    workflow.add_edge("extract_data", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def main() -> None:
    print("=== LangGraph Example 4: Human-in-the-Loop ===")
    app = build_graph()
    config = {"configurable": {"thread_id": "hitl-demo"}}

    # 场景 A:用户输入"ok",正常抓取
    print("\n--- 场景 A:用户确认 ok ---")
    result = app.invoke(
        {"user_goal": "抓取京东 iPhone 价格", "confirmed": False},
        config=config,
    )
    print(f"\n第 1 次 invoke(被 interrupt 暂停),最终 state: {result}")
    # 检查是否真的被暂停
    snapshot = app.get_state(config)
    print(f"  next: {snapshot.next}  tasks: {snapshot.tasks}")

    # 恢复:传入 Command(resume="ok")
    print("\n[人工回复] 传 Command(resume='ok'):")
    result = app.invoke(Command(resume="ok"), config=config)
    print(f"恢复后最终 state: {result}")

    # 场景 B:用户输入"cancel",直接结束
    print("\n\n--- 场景 B:用户取消 ---")
    config2 = {"configurable": {"thread_id": "hitl-demo-cancel"}}
    result = app.invoke(
        {"user_goal": "抓取豆瓣电影 TOP 250", "confirmed": False},
        config=config2,
    )
    print("\n[人工回复] 传 Command(resume='cancel'):")
    result = app.invoke(Command(resume="cancel"), config=config2)
    print(f"恢复后最终 state: {result}")


if __name__ == "__main__":
    main()
