"""Browser Agent 节点单元测试。

测试分两层:
1. BrowserState TypedDict / should_continue:纯逻辑
2. BrowserAgentNode 单步 + 重试:用 mock 替掉真实 Agent,验证重试/截图逻辑
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from browser_flow.agents.browser_node import (
    BrowserAgentNode,
    BrowserState,
    arun_plan,
    browser_agent_node,
    should_continue,
)

# ---- 纯逻辑 ----


class TestShouldContinue:
    def test_first_step_continue(self) -> None:
        state: BrowserState = {
            "sub_tasks": ["a", "b"],
            "current_step": 0,
            "errors": [],
        }
        assert should_continue(state) == "browser"

    def test_done_when_all_done(self) -> None:
        state: BrowserState = {
            "sub_tasks": ["a", "b"],
            "current_step": 2,
            "errors": [],
        }
        assert should_continue(state) == "end"

    def test_stop_when_last_error(self) -> None:
        state: BrowserState = {
            "sub_tasks": ["a", "b"],
            "current_step": 1,
            "errors": ["some error"],
        }
        assert should_continue(state) == "end"

    def test_empty_sub_tasks_end(self) -> None:
        state: BrowserState = {"sub_tasks": [], "current_step": 0, "errors": []}
        assert should_continue(state) == "end"


class TestBrowserState:
    def test_typed_dict_partial(self) -> None:
        """TypedDict total=False 时字段都是可选。"""
        state: BrowserState = {"sub_tasks": ["x"]}
        assert state["sub_tasks"] == ["x"]


# ---- Mock 单步:重试 + 截图 ----


class _FakeHistory:
    """模拟 browser-use History 对象。"""

    def __init__(self, result: str, screenshots: list | None = None) -> None:
        self._result = result
        self.screenshots = screenshots or []

    def final_result(self) -> str:
        return self._result


class TestBrowserAgentNodeMocked:
    @pytest.mark.asyncio
    async def test_run_one_success_no_retry(self) -> None:
        """单次成功:不应重试。"""
        node = BrowserAgentNode(max_retries=3)
        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(return_value=_FakeHistory("result-x", screenshots=[]))

        with patch("browser_flow.agents.browser_node.Agent", return_value=agent_instance):
            final, screenshot = await node.run_one("打开百度", 0)

        assert final == "result-x"
        assert screenshot == ""
        assert agent_instance.run.await_count == 1  # 没重试

    @pytest.mark.asyncio
    async def test_run_one_retries_then_succeeds(self) -> None:
        """前 2 次超时,第 3 次成功:应调 3 次 Agent。"""
        node = BrowserAgentNode(max_retries=3)
        agent_instance = MagicMock()
        # 第 1 次抛 TimeoutError,第 2 次抛 RuntimeError,第 3 次成功
        agent_instance.run = AsyncMock(
            side_effect=[
                TimeoutError("net1"),
                RuntimeError("net2"),
                _FakeHistory("finally"),
            ]
        )

        with patch("browser_flow.agents.browser_node.Agent", return_value=agent_instance):
            final, screenshot = await node.run_one("打开京东", 0)

        assert final == "finally"
        assert agent_instance.run.await_count == 3

    @pytest.mark.asyncio
    async def test_run_one_all_retries_fail(self) -> None:
        """全部 max_retries 次都失败:返回 ERROR 标记。"""
        node = BrowserAgentNode(max_retries=2)
        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(side_effect=RuntimeError("always fails"))

        with patch("browser_flow.agents.browser_node.Agent", return_value=agent_instance):
            final, screenshot = await node.run_one("打开", 0)

        assert final.startswith("[ERROR]")
        assert "always fails" in final
        assert screenshot == ""
        assert agent_instance.run.await_count == 2  # 不超过 max_retries

    @pytest.mark.asyncio
    async def test_run_one_non_retryable_error(self) -> None:
        """ValueError 不在重试白名单,应立刻 fail。"""
        node = BrowserAgentNode(max_retries=3)
        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(side_effect=ValueError("bad task"))

        with patch("browser_flow.agents.browser_node.Agent", return_value=agent_instance):
            final, _ = await node.run_one("打开", 0)

        assert final.startswith("[ERROR]")
        assert agent_instance.run.await_count == 1  # 不重试


# ---- 截图 base64 解码 ----


class TestScreenshotExtraction:
    @pytest.mark.asyncio
    async def test_screenshot_base64_decoded_and_saved(self, tmp_path) -> None:
        """_extract_last_screenshot 应正确解 base64 + 落盘。"""
        from browser_flow.agents.browser_node import _extract_last_screenshot

        # 1x1 透明 png 的 base64
        png_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        )
        history = _FakeHistory("ok", screenshots=[png_b64])

        b64 = await _extract_last_screenshot(history, 0, tmp_path)

        assert b64 == png_b64
        assert any(tmp_path.glob("step_000_*.png"))

    @pytest.mark.asyncio
    async def test_screenshot_empty_when_no_shots(self, tmp_path) -> None:
        from browser_flow.agents.browser_node import _extract_last_screenshot

        b64 = await _extract_last_screenshot(_FakeHistory("ok"), 0, tmp_path)
        assert b64 == ""

    @pytest.mark.asyncio
    async def test_screenshot_corrupt_returns_empty(self, tmp_path) -> None:
        """非法 base64 -> 吞异常返回空串。"""
        from browser_flow.agents.browser_node import _extract_last_screenshot

        b64 = await _extract_last_screenshot(
            _FakeHistory("ok", screenshots=["!!!not-base64!!!"]), 0, tmp_path
        )
        assert b64 == ""


# ---- LangGraph 节点(mock Agent 跑完一次)----


class TestBrowserNodeIntegration:
    @pytest.mark.asyncio
    async def test_abrowser_agent_node_progresses_step(self) -> None:
        """LangGraph 节点跑一步后,current_step 应 +1。"""
        from browser_flow.agents.browser_node import abrowser_agent_node

        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(return_value=_FakeHistory("page loaded"))

        with patch("browser_flow.agents.browser_node.Agent", return_value=agent_instance):
            state: BrowserState = {
                "sub_tasks": ["打开 baidu.com"],
                "current_step": 0,
                "screenshots": [],
                "step_results": [],
                "errors": [],
                "retry_counts": [],
            }
            update = await abrowser_agent_node(state)

        assert update["current_step"] == 1
        assert update["step_results"] == ["page loaded"]
        assert update["errors"] == []
        assert update["retry_counts"] == [2]  # max_retries=3 - 1(tenacity 写法)

    def test_browser_agent_node_sync_wrapper(self) -> None:
        """同步节点包装可用。"""
        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(return_value=_FakeHistory("ok"))

        with patch("browser_flow.agents.browser_node.Agent", return_value=agent_instance):
            state: BrowserState = {
                "sub_tasks": ["x"],
                "current_step": 0,
            }
            update = browser_agent_node(state)

        assert update["current_step"] == 1
        assert update["step_results"] == ["ok"]


# ---- arun_plan 串行跑 ----


@pytest.mark.asyncio
async def test_arun_plan_mocked() -> None:
    """Mocked: 2 步任务,1 成功 1 失败,验证 summary。"""
    agent_instance = MagicMock()
    agent_instance.run = AsyncMock(
        side_effect=[_FakeHistory("r1"), RuntimeError("step 2 failed")]
    )

    with patch("browser_flow.agents.browser_node.Agent", return_value=agent_instance):
        result = await arun_plan(["step A", "step B"], max_retries=1)

    assert len(result["step_results"]) == 2
    assert result["step_results"][0] == "r1"
    assert result["step_results"][1].startswith("[ERROR]")
    assert len(result["errors"]) == 1
    assert result["success_rate"] == 0.5
