"""Day 3 测试 2: checkpoint 真的能续跑 + HiTL 真的能等人工。"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


# ---- 图 A:带 checkpoint 的简单累加器 ----
class CounterState(TypedDict):
    counter: int
    log: list[str]


def increment(state: CounterState) -> dict:
    new_count = state["counter"] + 1
    return {"counter": new_count, "log": state["log"] + [f"step {new_count}"]}


def should_continue(state: CounterState) -> Literal["increment", "__end__"]:
    return "increment" if state["counter"] < 3 else END


def build_app_with_memory():
    memory = MemorySaver()
    workflow = StateGraph(CounterState)
    workflow.add_node("increment", increment)
    workflow.add_edge(START, "increment")
    workflow.add_conditional_edges("increment", should_continue)
    return workflow.compile(checkpointer=memory)


def test_get_state_returns_initial_values() -> None:
    app = build_app_with_memory()
    config = {"configurable": {"thread_id": "test-1"}}
    snapshot = app.get_state(config)
    # 没 invoke 过时,state 是 None
    assert snapshot.values == {}


def test_state_persists_across_invoke_calls() -> None:
    """核心断言:第 1 次 invoke 改的 state,在第 2 次 invoke 之前用 get_state 能拿到。"""
    app = build_app_with_memory()
    config = {"configurable": {"thread_id": "test-2"}}

    # 第 1 次 invoke:一次性跑完(只到 counter=3,因 should_continue 限制 < 3)
    app.invoke({"counter": 0, "log": []}, config=config)
    snapshot = app.get_state(config)
    # 跑完后 counter 应该是 3(因为 < 3 还会再跑一次到 3)
    assert snapshot.values["counter"] == 3
    assert snapshot.values["log"] == ["step 1", "step 2", "step 3"]


def test_state_persists_after_stream_interruption() -> None:
    """stream 过程中 break,checkpoint 应保留已执行的 state。"""
    app = build_app_with_memory()
    config = {"configurable": {"thread_id": "test-2b"}}

    # 用 stream 在第 1 步后立刻 break
    for _chunk in app.stream({"counter": 0, "log": []}, config=config):
        # 第 1 步跑完就退出(不要等全部跑完)
        break

    snapshot = app.get_state(config)
    # 第 1 步后 counter=1,即使后面还有 2 步没跑
    assert snapshot.values["counter"] == 1
    assert snapshot.values["log"] == ["step 1"]


# ---- 图 B:HiTL ----
class TaskState(TypedDict):
    confirmed: bool
    reply: str
    data: str


def ask(state: TaskState) -> dict:
    reply = interrupt("confirm?")
    confirmed = reply.strip().lower() == "yes"
    return {"confirmed": confirmed, "reply": reply}


def fetch(state: TaskState) -> dict:
    if not state["confirmed"]:
        return {"data": "(cancelled)"}
    return {"data": "fetched!"}


def build_hitl_app():
    def route(state: TaskState) -> str:
        return "fetch" if state["confirmed"] else END

    memory = MemorySaver()
    workflow = StateGraph(TaskState)
    workflow.add_node("ask", ask)
    workflow.add_node("fetch", fetch)
    workflow.add_edge(START, "ask")
    workflow.add_conditional_edges("ask", route)
    workflow.add_edge("fetch", END)
    return workflow.compile(checkpointer=memory)


def test_hitl_pauses_until_resume() -> None:
    """第 1 次 invoke 应被 interrupt 暂停,等 Command(resume) 才继续。"""
    app = build_hitl_app()
    config = {"configurable": {"thread_id": "hitl-1"}}

    # 第 1 次 invoke:会被 interrupt
    result = app.invoke({"confirmed": False, "reply": "", "data": ""}, config=config)
    # 暂停时 state 里会有 __interrupt__ 标记
    assert "__interrupt__" in result or not result.get("confirmed", True)
    # 此时 next 应该是 ("ask",)
    snapshot = app.get_state(config)
    assert snapshot.next == ("ask",)


def test_hitl_resume_yes() -> None:
    app = build_hitl_app()
    config = {"configurable": {"thread_id": "hitl-2"}}
    app.invoke({"confirmed": False, "reply": "", "data": ""}, config=config)
    result = app.invoke(Command(resume="yes"), config=config)
    assert result["confirmed"] is True
    assert result["reply"] == "yes"
    assert result["data"] == "fetched!"


def test_hitl_resume_cancel() -> None:
    """用户回答 "no" 时:confirmed=False,路由到 END(fetch 节点不跑)。"""
    app = build_hitl_app()
    config = {"configurable": {"thread_id": "hitl-3"}}
    app.invoke({"confirmed": False, "reply": "", "data": ""}, config=config)
    result = app.invoke(Command(resume="no"), config=config)
    assert result["confirmed"] is False
    assert result["reply"] == "no"
    # confirmed=False 时,条件路由返 END,fetch 节点不会执行
    # 所以 data 保留初始空字符串
    assert result["data"] == ""
