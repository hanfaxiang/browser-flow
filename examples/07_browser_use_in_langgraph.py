"""Day 4 Example 3: Browser-Use 接入 LangGraph

目标:
    1. 学会把 Browser-Use 包成 LangGraph 节点
    2. 看到 Agent.run_sync()(同步版)在节点里调用
    3. 验证 LangGraph 的 state 机制能串起多步浏览器任务

核心概念:
    - LangGraph 节点 = 普通 Python 函数(state in -> state out)
    - Agent.run_sync() = run() 的同步包装,适合在节点里调用
    - 这种"LangGraph 装 Agent"是 Day 8 多 Agent 架构的基础

应用场景:
    - 节点 1:规划(planning agent)
    - 节点 2:浏览器执行(browser-use agent)
    - 节点 3:验证(verifier agent)
    - 全部串在 LangGraph 里,用 checkpoint 续跑
"""

from __future__ import annotations

import os
from typing import TypedDict

from browser_use import Agent
from langgraph.graph import END, START, StateGraph

from browser_flow.browser import get_browser_profile
from browser_flow.llm import get_llm


class BrowserTaskState(TypedDict):
    """浏览器任务的状态:输入 + 输出。"""

    task: str
    result: str
    success: bool


def run_browser_agent(state: BrowserTaskState) -> dict:
    """核心节点:用 Browser-Use Agent 执行任务。

    这是关键模式:
      - LangGraph 节点函数 = 普通 sync 函数
      - 内部用 Agent.run_sync() 阻塞跑 Agent
      - 返回 dict(增量更新 state)
    """
    print(f"  [节点] 收到任务: {state['task']}")

    llm = get_llm()
    agent = Agent(task=state["task"], llm=llm, browser_profile=get_browser_profile())

    # 同步版:在节点里阻塞调用,跑完才返回
    history = agent.run_sync(max_steps=10)

    final = history.final_result()
    success = bool(final)
    print(f"  [节点] 完成,success={success}")

    # 返回 dict,LangGraph 会 merge 进 state
    return {"result": str(final) if final else "", "success": success}


def build_graph():
    """最小 LangGraph:START -> browser -> END。"""
    workflow = StateGraph(BrowserTaskState)
    workflow.add_node("browser", run_browser_agent)
    workflow.add_edge(START, "browser")
    workflow.add_edge("browser", END)
    return workflow.compile()


def main() -> None:
    print("=== Browser-Use + LangGraph ===")

    app = build_graph()

    initial: BrowserTaskState = {
        "task": "打开 https://quotes.toscrape.com/ 抓取前 2 条名言,用一句话总结",
        "result": "",
        "success": False,
    }
    print(f"输入: {initial}")

    # LangGraph sync invoke(在 async 环境里可以用 ainvoke)
    final_state = app.invoke(initial)

    print("\n=== 最终 state ===")
    print(f"task: {final_state['task']}")
    print(f"success: {final_state['success']}")
    print(f"result: {final_state['result']}")


if __name__ == "__main__":
    if not (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        raise SystemExit("需要 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量")
    main()
