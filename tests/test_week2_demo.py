"""Week 2 集成测试:Planning + Browser + Extraction 全链路 mock。

验证"打开 quotes.toscrape.com,提取所有名言"场景能跑通。
不真跑 Browser(太慢,留给 examples/14 --real)。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from browser_flow.agents.supervisor import build_supervisor_graph


class Quote(BaseModel):
    text: str
    author: str


class Week2DemoTest:
    """Day 14 Week 2 收尾 demo。"""


@pytest.fixture
def mocked_three_agents() -> None:
    """Patch 三层 Agent 的真实依赖。"""
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(
        side_effect=[
            # 1. Planning
            MagicMock(
                completion='{"sub_tasks": ['
                '"打开 quotes.toscrape.com", '
                '"抓取页面上所有名言和作者"], '
                '"estimated_steps": 2, '
                '"rationale": "静态抓取无需翻页"}'
            ),
            # 2. Extraction
            MagicMock(
                completion='{"text": "The world as we have created it...", '
                '"author": "Albert Einstein"}'
            ),
        ]
    )
    with (
        patch("browser_flow.agents.planning.get_llm", return_value=fake_llm),
        patch("browser_flow.agents.extraction.get_llm", return_value=fake_llm),
        patch(
            "browser_flow.agents.supervisor.browser_agent_node",
            return_value={
                "current_step": 2,
                "step_results": ["raw quote 1", "raw quote 2"],
                "errors": [],
            },
        ),
    ):
        yield


def test_week2_quotes_demo_full_chain(mocked_three_agents) -> None:
    """完整链路:planning -> browser(2步) -> extraction -> END。"""
    graph = build_supervisor_graph(target_schema=Quote)

    result = graph.invoke(
        {"user_task": "打开 quotes.toscrape.com 抓取所有名言和作者"}
    )

    # Planning 拆出 2 步
    assert len(result["sub_tasks"]) == 2
    assert result["estimated_steps"] == 2

    # Browser 跑完 2 步
    assert result["current_step"] == 2
    assert len(result["step_results"]) == 2
    assert result["errors"] == []

    # Extraction 产出结构化
    assert isinstance(result["extracted"], Quote)
    assert result["extracted_dict"]["author"] == "Albert Einstein"
    assert result["extraction_error"] == ""


def test_week2_demo_with_partial_failure(mocked_three_agents) -> None:
    """Browser 第 2 步失败:图仍能跑到 extraction,errors 被记录。"""
    # 重新 patch 一个会"失败"的 browser
    with patch(
        "browser_flow.agents.supervisor.browser_agent_node",
        side_effect=[
            # step 1 OK
            {"current_step": 1, "step_results": ["raw1"], "errors": []},
            # step 2 FAIL
            {
                "current_step": 2,
                "step_results": ["raw1", "[ERROR] timeout"],
                "errors": ["[ERROR] timeout"],
            },
        ],
    ):
        graph = build_supervisor_graph(target_schema=Quote)
        result = graph.invoke({"user_task": "抓名言"})

    # Browser 跑完 2 步(step 1 OK,step 2 FAIL)
    assert result["current_step"] == 2
    assert len(result["errors"]) == 1
    assert result["errors"][0] == "[ERROR] timeout"
    # Extraction 仍跑(用最后一条 step_result)
    assert isinstance(result["extracted"], Quote)


def test_week2_demo_planning_history_tracks_revisions() -> None:
    """多轮规划:planning_history 累积每个版本(给回放 / 调试用)。"""
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(
        side_effect=[
            # planning
            MagicMock(
                completion='{"sub_tasks": ["a", "b"], '
                '"estimated_steps": 2, "rationale": "v1"}'
            ),
            # extraction
            MagicMock(completion='{"text": "t", "author": "a"}'),
        ]
    )

    with (
        patch("browser_flow.agents.planning.get_llm", return_value=fake_llm),
        patch("browser_flow.agents.extraction.get_llm", return_value=fake_llm),
        patch(
            "browser_flow.agents.supervisor.browser_agent_node",
            return_value={
                "current_step": 2,
                "step_results": ["x"],
                "errors": [],
            },
        ),
    ):
        graph = build_supervisor_graph(target_schema=Quote)
        result = graph.invoke({"user_task": "test"})

    # planning_history 应有 1 项(本次)
    assert len(result["planning_history"]) == 1
    assert result["planning_history"][0]["rationale"] == "v1"
    assert result["planning_history"][0]["sub_tasks"] == ["a", "b"]
