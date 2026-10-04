"""Supervisor Graph 测试。

主要测图结构,不真跑 Browser(太慢)。用 mock 替掉 browser_agent_node 和 aextract。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from browser_flow.agents.supervisor import (
    SupervisorState,
    _planning_for_graph,
    build_supervisor_graph,
)


class _Quote(BaseModel):
    text: str
    author: str


def test_planning_for_graph_handles_empty_task() -> None:
    state: SupervisorState = {"user_task": ""}
    update = _planning_for_graph(state)
    assert update["sub_tasks"] == []
    assert update["estimated_steps"] == 0


def test_planning_for_graph_runs_real_planning() -> None:
    """无 loop 同步跑:用 mock LLM 走 Planning 子树。"""

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(
        return_value=MagicMock(
            completion='{"sub_tasks": ["打开 a"], "estimated_steps": 1, "rationale": "r"}'
        )
    )

    with patch("browser_flow.agents.planning.get_llm", return_value=fake_llm):
        state: SupervisorState = {"user_task": "打开 a"}
        update = _planning_for_graph(state)

    assert update["sub_tasks"] == ["打开 a"]
    assert update["current_step"] == 0
    assert update["planning_history"]  # 含一个 dict


def test_build_supervisor_graph_returns_compiled() -> None:
    """构造图能成功,返回 CompiledStateGraph。"""
    graph = build_supervisor_graph(target_schema=_Quote)
    assert graph is not None
    # 验证节点数
    assert hasattr(graph, "invoke") and hasattr(graph, "ainvoke")


def test_supervisor_graph_no_target_schema_marks_error() -> None:
    """target_schema=None 时,extraction 节点会返回 extraction_error。"""
    # 不走图(避免 mock browser_node 在 LangGraph compile 后无生效的坑),
    # 直接调 _extraction_for_graph 这个图内包装函数。

    from browser_flow.agents.supervisor import _GRAPH_TARGET_SCHEMA, _extraction_for_graph

    _GRAPH_TARGET_SCHEMA["schema"] = None  # 显式置 None
    try:
        result = _extraction_for_graph({"step_results": ["raw text"]})
    finally:
        _GRAPH_TARGET_SCHEMA.pop("schema", None)

    assert "extraction_error" in result
    assert "target_schema" in result["extraction_error"]


@pytest.mark.asyncio
async def test_supervisor_with_mocked_agents_full_flow() -> None:
    """全程 mock 三层 Agent,验证图能从 planning 跑到 END,产出 extracted。"""
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(
        side_effect=[
            # planning call
            MagicMock(
                completion='{"sub_tasks": ["打开 baidu"], "estimated_steps": 1, "rationale": "r"}'
            ),
            # extraction call
            MagicMock(completion='{"text": "hello", "author": "world"}'),
        ]
    )

    with (
        patch("browser_flow.agents.planning.get_llm", return_value=fake_llm),
        patch("browser_flow.agents.extraction.get_llm", return_value=fake_llm),
        patch(
            "browser_flow.agents.supervisor.browser_agent_node",
            return_value={"current_step": 1, "step_results": ["browser raw"], "errors": []},
        ),
    ):
        graph = build_supervisor_graph(target_schema=_Quote)
        result = graph.invoke({"user_task": "打开 baidu 抓第一条"})

    assert result["user_task"] == "打开 baidu 抓第一条"
    assert result["sub_tasks"] == ["打开 baidu"]
    assert result["step_results"] == ["browser raw"]
    assert isinstance(result["extracted"], _Quote)
    assert result["extracted_dict"] == {"text": "hello", "author": "world"}
    assert result["extraction_error"] == ""
