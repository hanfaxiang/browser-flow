"""Supervisor Graph:把 Planning + Browser + Extraction 串成 LangGraph 图。

报告 Day 12-13 要点:
    [ ] StateGraph 编排三 Agent
    [ ] 跑通第一个完整场景

图结构:
    START -> planning -> browser_loop -> extraction -> END

    browser_loop:
        browser 节点(跑一步)
        ↓ should_continue
        ├─ 还有步数 -> browser(继续)
        └─ 完成 -> extraction

State(继承自三 Agent 各自的子集):
    - PlanningState:user_task / sub_tasks / current_step / estimated_steps / rationale / history
    - BrowserState:current_step / step_results / screenshots / errors / retry_counts
    - ExtractionState:extracted / extracted_dict / extraction_error

可配置 target schema(给 extraction_node 用):
    - 通过 graph 构造参数 `target_schema: type[BaseModel]`
    - 给静态图,避免节点闭包复杂度

跑法(给 example / 测试):
    graph = build_supervisor_graph(target_schema=Quote)
    result = graph.invoke({"user_task": "打开 quotes.toscrape.com 抓第一条名言"})

注意:
    - Planning 节点用 _plan_smart(在 loop 里也安全)
    - Browser 节点用真实的 abrowser_agent_node(慢,example 慎跑)
    - Extraction 节点固定 target_schema
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, TypedDict, TypeVar

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from browser_flow.agents.browser_node import (
    abrowser_agent_node,
    browser_agent_node,
    should_continue,
)
from browser_flow.agents.extraction import aextraction_node
from browser_flow.agents.planning import _plan_smart

T = TypeVar("T", bound=BaseModel)


class SupervisorState(TypedDict, total=False):
    """组合三 Agent 的 State。

    字段:
        来自 PlanningState:
                user_task: str
                sub_tasks: list[str]
                estimated_steps: int
                rationale: str
                planning_history: list[dict]
            来自 BrowserState:
                current_step: int
                screenshots: list[str]
                step_results: list[str]
                errors: list[str]
                retry_counts: list[int]
            来自 ExtractionState:
                extracted: Any(BaseModel 实例)
                extracted_dict: dict
                extraction_error: str
            额外:
                target_schema_name: str(给 traceability 链参考)
    """

    user_task: str
    sub_tasks: list[str]
    current_step: int
    estimated_steps: int
    rationale: str
    planning_history: list[dict[str, Any]]
    screenshots: list[str]
    step_results: list[str]
    errors: list[str]
    retry_counts: list[int]
    extracted: Any
    extracted_dict: dict[str, Any]
    extraction_error: str


def _planning_for_graph(state: SupervisorState) -> dict[str, Any]:
    """图内 Planner:在已有 loop / 无 loop 都能跑。"""
    user_task = state.get("user_task", "")
    if not user_task:
        return {"sub_tasks": [], "estimated_steps": 0, "rationale": "no task"}

    plan_obj = _plan_smart(user_task)
    return {
        "sub_tasks": plan_obj.sub_tasks,
        "current_step": 0,
        "estimated_steps": plan_obj.estimated_steps,
        "rationale": plan_obj.rationale,
        "planning_history": state.get("planning_history", []) + [plan_obj.model_dump()],
    }


def _extraction_for_graph(state: SupervisorState) -> dict[str, Any]:
    """图内 Extraction:从 state 取 target_schema(用 module-level 配置)。"""
    target = _GRAPH_TARGET_SCHEMA.get("schema")
    if target is None:
        return {"extraction_error": "target_schema not configured"}

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(aextraction_node(state, target))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, aextraction_node(state, target)).result()


# graph-build 时填入,闭包太绕
_GRAPH_TARGET_SCHEMA: dict[str, Any] = {}


def build_supervisor_graph(
    target_schema: type[BaseModel] | None = None,
    use_async_nodes: bool = False,
) -> Any:
    """构造 Supervisor 图。

    Args:
        target_schema: Extraction 要填的 Pydantic 类型。None 时 extraction 节点会返回错误。
        use_async_nodes: True 用 ainvoke(图) 异步节点;False 用同步包装(嵌套 loop 安全)。

    Returns:
        CompiledStateGraph,可 invoke / ainvoke。
    """
    if target_schema is not None:
        _GRAPH_TARGET_SCHEMA["schema"] = target_schema

    workflow: StateGraph = StateGraph(SupervisorState)

    # 节点注册
    workflow.add_node("planning", _planning_for_graph)
    if use_async_nodes:
        workflow.add_node("browser", abrowser_agent_node)
        workflow.add_node("extraction", aextraction_node)
    else:
        workflow.add_node("browser", browser_agent_node)
        workflow.add_node("extraction", _extraction_for_graph)

    # 边
    workflow.add_edge(START, "planning")
    workflow.add_edge("planning", "browser")

    # 条件边:browser 跑完后,还有步数 -> 再 browser;否则 -> extraction
    workflow.add_conditional_edges(
        "browser",
        should_continue,
        {
            "browser": "browser",
            "end": "extraction",
        },
    )
    workflow.add_edge("extraction", END)

    return workflow.compile()


# ---- 简洁运行入口 ----


async def arun_supervisor(
    user_task: str,
    target_schema: type[BaseModel] | None = None,
) -> SupervisorState:
    """异步入口:从 user_task 跑完整个 supervisor 图,返回 final state。"""
    graph = build_supervisor_graph(target_schema=target_schema, use_async_nodes=True)
    initial: SupervisorState = {"user_task": user_task}
    return await graph.ainvoke(initial)


def run_supervisor(
    user_task: str,
    target_schema: type[BaseModel] | None = None,
) -> SupervisorState:
    """同步入口。"""
    return asyncio.run(arun_supervisor(user_task, target_schema))
