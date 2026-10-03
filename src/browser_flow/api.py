"""统一 API 入口:同步 / 异步 / 流式 三种用法。

为什么需要这个:
    1. Browser-Use 自带 run() 是 async,run_sync() 是 sync wrapper,
      Web 后端(Flask/FastAPI)想用同步,数据科学脚本想用同步,
      异步服务想用 async — 三种都要
    2. 流式输出(每 step 一次回调)对长任务 / UI 反馈很有用,
      Browser-Use 没原生 stream,我们包一层 on_step_start / on_step_end
    3. 统一错误处理,任何异常包成 BrowserFlowError 让上层好处理

设计:
    - run_sync(task, ...)         : 同步,返回 AgentHistoryList
    - arun(task, ...)             : 异步,返回 AgentHistoryList
    - stream(task, ...)           : 异步生成器,每 step 一次 yield AgentStepEvent
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from typing import Any

from browser_use import Agent

from browser_flow.browser import get_browser_profile
from browser_flow.llm import get_llm


class BrowserFlowError(RuntimeError):
    """包装 Browser-Use 抛出的异常,加一层统一错误类型。"""


class AgentStepEvent:
    """单步执行事件。流式 API 每步产出一个。

    Attributes:
        step:第几步(从 1 开始)
        url:当前页面 URL
        thought:模型这一步的思考文本
        action_name:这一步执行的动作名(click / type / done 等)
        done:Agent 是否判断任务完成
    """

    def __init__(
        self,
        step: int,
        url: str | None,
        thought: str | None,
        action_name: str | None,
        done: bool,
    ) -> None:
        self.step = step
        self.url = url
        self.thought = thought
        self.action_name = action_name
        self.done = done

    def __repr__(self) -> str:
        return (
            f"AgentStepEvent(step={self.step}, "
            f"action={self.action_name!r}, "
            f"done={self.done}, "
            f"url={self.url!r})"
        )


def _build_agent(
    task: str,
    llm: Any | None = None,
    browser_profile: Any | None = None,
    **kwargs: Any,
) -> Agent:
    """统一构造 Agent。私有,供 sync/async/stream 三入口共用。"""
    return Agent(
        task=task,
        llm=llm or get_llm(),
        browser_profile=browser_profile or get_browser_profile(),
        **kwargs,
    )


def run_sync(task: str, **kwargs: Any):
    """同步入口。

    API:
            task:自然语言任务描述
            kwargs:透传给 Agent 的其它参数(如 output_model_schema)

    Returns:
            AgentHistoryList(有 .final_result / .is_successful / .number_of_steps 等)

    Raises:
            BrowserFlowError:运行失败
    """
    try:
        agent = _build_agent(task, **kwargs)
        return agent.run_sync()
    except BrowserFlowError:
        raise
    except Exception as e:
        raise BrowserFlowError(f"Agent 运行失败: {e}") from e


async def arun(task: str, **kwargs: Any):
    """异步入口。

    API:
            task:自然语言任务描述
            kwargs:透传给 Agent 的其它参数

    Returns:
            AgentHistoryList
    """
    try:
        agent = _build_agent(task, **kwargs)
        return await agent.run()
    except BrowserFlowError:
        raise
    except Exception as e:
        raise BrowserFlowError(f"Agent 运行失败: {e}") from e


async def stream(
    task: str,
    **kwargs: Any,
) -> AsyncIterator[AgentStepEvent]:
    """流式入口。异步生成器,每 step 产出一个 AgentStepEvent。

    API:
            task:自然语言任务描述
            kwargs:透传给 Agent 的其它参数

    Yields:
            AgentStepEvent(每步一个,包括一个 done=True 收尾)

    实现:
        在 agent.run() 跑在后台 task,回调通过 asyncio.Event + shared list
        推过来。比 Queue 简单,因为回调里**不能 await 阻塞**,
        Queue.get() 会和回调里 queue.put 死锁(同 loop 串行)。

    Example:
            ```python
            async for ev in stream("去 quotes.toscrape.com 抓 3 条名言"):
                print(ev)
            ```
    """
    agent = _build_agent(task, **kwargs)

    # 用 list + Event 通信;回调里 append + set event,生成器里 wait + drain
    pending: list[AgentStepEvent] = []
    new_event = asyncio.Event()
    agent_done = False
    agent_error: list[Exception] = []

    async def _on_step_start(a: Agent) -> None:
        # 抽取这一步的数据
        step = a.history.number_of_steps()
        url: str | None = None
        thought: str | None = None
        action_name: str | None = None
        try:
            if a.history.history:
                last = a.history.history[-1]
                url = getattr(last.state, "url", None) if last.state else None
                if last.model_output and last.model_output.thinking:
                    thought = last.model_output.thinking
                if last.model_output and last.model_output.action:
                    action_name = last.model_output.action[0].__class__.__name__
        except Exception:
            pass

        event = AgentStepEvent(
            step=step,
            url=url,
            thought=thought,
            action_name=action_name,
            done=False,
        )
        pending.append(event)
        new_event.set()

    async def _runner() -> None:
        nonlocal agent_done
        try:
            await agent.run(on_step_start=_on_step_start)
        except asyncio.CancelledError:
            # 消费者 break 后我们主动 cancel runner,这是预期的
            pass
        except Exception as e:
            agent_error.append(e)
        finally:
            agent_done = True
            # 推一个 done 事件收尾;access history 时出错则 step=0
            try:
                step = agent.history.number_of_steps() if agent.history else 0
            except AttributeError:
                step = 0
            pending.append(
                AgentStepEvent(
                    step=step,
                    url=None,
                    thought=None,
                    action_name=None,
                    done=True,
                )
            )
            new_event.set()

    runner_task = asyncio.create_task(_runner())

    try:
        while True:
            # 等新事件或 agent 完成
            if not pending:
                await new_event.wait()
                new_event.clear()

            # 排空队列里所有事件
            while pending:
                event = pending.pop(0)
                yield event
                if event.done:
                    # 收尾事件,结束流
                    return
            # 如果 agent 已经 done 但 pending 空(不会发生,反正兜底)
            if agent_done:
                return
    finally:
        if not runner_task.done():
            runner_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await runner_task
        if agent_error:
            raise BrowserFlowError(f"Agent 运行失败: {agent_error[0]}") from agent_error[0]
