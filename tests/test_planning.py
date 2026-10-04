"""Planning Agent 单元测试。

测试分两层:
1. _extract_json / TaskPlan:不调 LLM,纯逻辑(快速,无网络)
2. aplan / plan:需要 API key,只在有 key 时跑(@pytest.mark.skipif)
"""

from __future__ import annotations

import os

import pytest

from browser_flow.agents.planning import (
    REFINITION_PROMPT,
    SYSTEM_PROMPT,
    PlanningState,
    TaskPlan,
    _extract_json,
    aplan,
    aplan_with_feedback,
    plan,
    plan_with_feedback,
    planning_node,
)

# ---- 纯逻辑:JSON 抽取 ----


class TestExtractJson:
    def test_fenced_json(self) -> None:
        text = "思考中...\n```json\n{\"a\": 1}\n```\n完成"
        assert _extract_json(text) == {"a": 1}

    def test_bare_json_with_prefix(self) -> None:
        text = "好的:\n{\"sub_tasks\": [\"x\"], \"estimated_steps\": 1}"
        assert _extract_json(text)["sub_tasks"] == ["x"]

    def test_nested_json(self) -> None:
        text = '```json\n{"sub_tasks": ["a", "c"], "n": {"k": "v"}}\n```'

        result = _extract_json(text)
        assert result["sub_tasks"] == ["a", "c"]
        assert result["n"] == {"k": "v"}

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="空内容"):
            _extract_json("")

    def test_no_json_raises(self) -> None:
        with pytest.raises(ValueError, match="无 JSON"):
            _extract_json("我没法回答这个问题")


# ---- 纯逻辑:TaskPlan 校验 ----


class TestTaskPlan:
    def test_minimal(self) -> None:
        p = TaskPlan(sub_tasks=["打开网站"], estimated_steps=1)
        assert len(p.sub_tasks) == 1
        assert p.rationale == ""

    def test_empty_subtasks_rejected(self) -> None:
        with pytest.raises(ValueError):
            TaskPlan(sub_tasks=[], estimated_steps=1)

    def test_too_many_subtasks_rejected(self) -> None:
        with pytest.raises(ValueError):
            TaskPlan(sub_tasks=[f"step {i}" for i in range(25)], estimated_steps=25)

    def test_negative_steps_rejected(self) -> None:
        with pytest.raises(ValueError):
            TaskPlan(sub_tasks=["x"], estimated_steps=0)

    def test_rationale_optional(self) -> None:
        p = TaskPlan(
            sub_tasks=["打开", "抓取"],
            estimated_steps=2,
            rationale="标准抓取",
        )
        assert p.rationale == "标准抓取"


# ---- 端到端:需要 API key ----


HAS_KEY = bool(os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY"))


@pytest.mark.skipif(not HAS_KEY, reason="需要 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")
class TestPlanningEndToEnd:
    @pytest.mark.asyncio
    async def test_aplan_quote_scraping(self) -> None:
        """拆 quotes 抓取任务,应得到 3-8 步。"""
        plan_obj = await aplan("打开 quotes.toscrape.com 抓取第一页所有名言和作者")

        assert 1 <= len(plan_obj.sub_tasks) <= 20
        assert 1 <= plan_obj.estimated_steps <= 50
        # 第一步应该是"打开 ..."
        assert "打开" in plan_obj.sub_tasks[0]

    @pytest.mark.asyncio
    async def test_aplan_complex_task(self) -> None:
        """拆京东搜索任务,应至少 4 步(打开/搜/抓/保存)。"""
        plan_obj = await aplan(
            "打开京东搜索 iPhone,提取前 10 个商品标题和价格,保存为 JSON"
        )

        assert len(plan_obj.sub_tasks) >= 3

    def test_plan_sync_wrapper(self) -> None:
        """plan() 同步入口能用。"""
        result = plan("打开百度搜索 LangGraph 教程")
        assert isinstance(result, TaskPlan)
        assert len(result.sub_tasks) >= 1


# ---- prompt 完整性检查(防止改坏 prompt)----


def test_system_prompt_has_key_sections() -> None:
    """SYSTEM_PROMPT 必备的 4 个关键字:拆分原则 / 步骤数 / 单一动作 / 示例。"""
    for kw in ("拆分原则", "3-8", "单一浏览器动作", "示例"):
        assert kw in SYSTEM_PROMPT, f"SYSTEM_PROMPT 缺少关键字: {kw}"


# ---- Day 9: 多轮反馈 ----


class TestRefinementPrompt:
    def test_refinement_prompt_has_placeholders(self) -> None:
        for ph in ("{user_task}", "{previous_plan}", "{feedback}"):
            assert ph in REFINITION_PROMPT, f"REFINITION_PROMPT 缺少 {ph}"


@pytest.mark.skipif(not HAS_KEY, reason="需要 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")
class TestPlanningFeedback:
    @pytest.mark.asyncio
    async def test_aplan_with_feedback_split_finer(self) -> None:
        """原计划 5 步,反馈"再拆细",应得到 ≥5 步。"""
        original = await aplan("打开京东搜索 iPhone 提取价格")

        refined = await aplan_with_feedback(
            user_task="打开京东搜索 iPhone 提取价格",
            previous=original,
            feedback="把'抓取商品'拆细:分两条,一条抓标题和价格,一条抓详情页评分",
        )

        assert len(refined.sub_tasks) >= len(original.sub_tasks)
        assert refined.estimated_steps >= original.estimated_steps

    def test_plan_with_feedback_sync(self) -> None:
        """同步 plan_with_feedback 可用。"""
        first = plan("打开百度")
        second = plan_with_feedback(
            user_task="打开百度",
            previous=first,
            feedback="把打开步骤合并掉,只要一步",
        )
        assert isinstance(second, TaskPlan)


# ---- Day 9: LangGraph State + 节点 ----


class TestPlanningState:
    def test_typed_dict_fields(self) -> None:
        """PlanningState 暴露关键字段。"""
        state: PlanningState = {
            "user_task": "打开百度",
            "sub_tasks": ["打开 baidu.com"],
            "current_step": 0,
            "estimated_steps": 1,
        }
        assert state["user_task"] == "打开百度"
        assert "planning_history" not in state  # total=False 时可选

    def test_planning_node_returns_partial(self) -> None:
        """planning_node 输入空 user_task 返回安全降级。"""
        result = planning_node({"user_task": ""})  # type: ignore[typeddict-item]
        assert result["sub_tasks"] == []
        assert result["estimated_steps"] == 0
