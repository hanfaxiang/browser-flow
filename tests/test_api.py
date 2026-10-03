"""测试 api.py 的纯逻辑(不真启动浏览器)。"""

from __future__ import annotations

import pytest

from browser_flow.api import AgentStepEvent, BrowserFlowError


class TestAgentStepEvent:
    """AgentStepEvent 数据类。"""

    def test_repr_contains_key_fields(self) -> None:
        event = AgentStepEvent(
            step=1,
            url="https://example.com",
            thought="click button",
            action_name="Click",
            done=False,
        )
        r = repr(event)
        assert "step=1" in r
        assert "Click" in r
        assert "example.com" in r

    def test_done_flag_round_trip(self) -> None:
        event = AgentStepEvent(step=2, url=None, thought=None, action_name=None, done=True)
        assert event.done is True


class TestRunSyncErrorWrapping:
    """run_sync 必须把内部异常包成 BrowserFlowError。"""

    def test_raises_browserflow_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # mock get_llm,让 build_agent 抛错
        from browser_flow import api

        def boom() -> None:
            raise RuntimeError("simulated LLM failure")

        monkeypatch.setattr(api, "get_llm", boom)

        with pytest.raises(BrowserFlowError) as exc_info:
            api.run_sync("anything")
        assert "Agent 运行失败" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, RuntimeError)


class TestArunErrorWrapping:
    """arun 也要包装异常。"""

    async def test_raises_browserflow_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from browser_flow import api

        def boom() -> None:
            raise RuntimeError("simulated build failure")

        monkeypatch.setattr(api, "get_llm", boom)

        with pytest.raises(BrowserFlowError):
            await api.arun("anything")


class TestStreamConsumerBreak:
    """stream 消费者主动 break 时不应留后台 task 永远卡住。"""

    async def test_break_out_early_does_not_deadlock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from browser_flow import api

        # 让 _build_agent 立刻返回一个 mock agent,run() 永远不返回
        class _History:
            history = []
            def number_of_steps(self):
                return 0

        class _StuckAgent:
            history = _History()
            async def run(self, on_step_start=None, **_kw):
                # 调一下回调模拟一次 step,然后 hang
                if on_step_start:
                    await on_step_start(self)
                import asyncio
                await asyncio.Event().wait()  # 永远等

        def fake_build(task, **kwargs):  # noqa: ARG001
            return _StuckAgent()

        monkeypatch.setattr(api, "_build_agent", fake_build)

        # 消费者只取一个事件就 break,不能卡 30 秒
        import asyncio

        async def consume_one_then_break() -> None:
            gen = api.stream("anything")
            try:
                async for _event in gen:
                    break  # 只取第一个
            finally:
                await gen.aclose()

        # 加 5 秒超时,过了就失败
        await asyncio.wait_for(consume_one_then_break(), timeout=5.0)
