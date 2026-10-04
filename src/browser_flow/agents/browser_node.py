"""Browser Agent: 把 browser-use 包装成 LangGraph 节点。

报告 Day 10-11 要点:
    [ ] 包装 Browser-Use 为 LangGraph 节点
    [ ] 加入截图存档
    [ ] 加入错误捕获
    [ ] 加入重试逻辑(指数退避)

设计:
    - BrowserAgentNode 类:持有一个 Agent,提供 run_one_step() 异步入口
    - browser_agent_node(state) -> dict:LangGraph 同步/异步节点函数
      从 state['sub_tasks'][state['current_step']] 取单步任务,
      调 Agent,捕获异常,tenacity 退避重试,截图存到 state['screenshots']。
    - 单步重试粒度比"整个任务"更细:某一步失败可单独重试 / 跳步。

注意 browser-use 的 Agent.run() 本身就是大循环,会一直跑到 final_result
或 max_steps。我们这里用 "把整个 sub_task 当一个独立任务给 Agent" 的方式,
而不是 "每一步交互都起一个 Agent"(那样太重)。
"""

from __future__ import annotations

import asyncio
import base64
import time
from pathlib import Path
from typing import Any, TypedDict

from browser_use import Agent
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from browser_flow.browser import get_browser_profile
from browser_flow.llm import get_llm

# ---- 类型 / State ----


class BrowserState(TypedDict, total=False):
    """LangGraph State 里的 Browser 子集(给 Day 12 Supervisor 用)。

    字段:
        current_step: 0-indexed,当前执行第几步子任务
        sub_tasks: 来自 PlanningState
        screenshots: 每步截图的 base64 编码列表(可用于回看 / 调试)
        step_results: 每步执行结果(str,通常是 Agent final_result())
        errors: 各步错误历史(用于重试 / 调试)
        retry_counts: 各步已重试次数
    """

    current_step: int
    sub_tasks: list[str]
    screenshots: list[str]
    step_results: list[str]
    errors: list[str]
    retry_counts: list[int]


class BrowserAgentNode:
    """单步 Browser Agent 节点:接收 sub_task,跑 Agent,捕获异常,保存截图。

    用法(同步节点):
        node = BrowserAgentNode(max_steps=10, max_retries=3)
        result = node.run_one_sync("打开百度搜索 LangGraph")

    用法(async 节点):
        result = await node.run_one("打开京东搜索 iPhone")
    """

    def __init__(
        self,
        max_steps: int = 10,
        max_retries: int = 3,
        screenshot_dir: str | None = None,
        headless: bool | None = None,
    ) -> None:
        self.max_steps = max_steps
        self.max_retries = max_retries
        self.screenshot_dir = Path(screenshot_dir or "screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless

    def _build_agent(self, sub_task: str) -> Agent:
        """每个 sub_task 起一个新 Agent(避免 session 跨任务污染)。"""
        return Agent(
            task=sub_task,
            llm=get_llm(),
            browser_profile=get_browser_profile(headless=self.headless),
        )

    async def run_one(self, sub_task: str, step_idx: int) -> tuple[str, str]:
        """异步跑一个子任务。

        Returns:
            (final_result_str, screenshot_base64)
            final_result 空串表示失败。
        """
        last_exc: Exception | None = None
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                retry=retry_if_exception_type((RuntimeError, TimeoutError, ConnectionError)),
                reraise=True,
            ):
                with attempt:
                    if attempt.retry_state.attempt_number > 1:
                        n = attempt.retry_state.attempt_number
                        preview = sub_task[:40]
                        print(f"    [browser-node] 重试第 {n} 次: {preview}")
                    final, screenshot_b64 = await self._attempt(sub_task, step_idx)
                    return final, screenshot_b64
        except RetryError as exc:
            last_exc = exc
        except Exception as exc:  # noqa: BLE001
            last_exc = exc

        return f"[ERROR] {last_exc}", ""

    async def _attempt(self, sub_task: str, step_idx: int) -> tuple[str, str]:
        """单次尝试:跑 Agent + 截图。"""
        agent = self._build_agent(sub_task)
        history = await agent.run(max_steps=self.max_steps)
        final = history.final_result() or ""

        # 截图:browser-use history.last_action / screenshots 都可以
        screenshot_b64 = await _extract_last_screenshot(history, step_idx, self.screenshot_dir)
        return str(final), screenshot_b64

    def run_one_sync(self, sub_task: str, step_idx: int) -> tuple[str, str]:
        """同步入口:包 asyncio.run。"""
        return asyncio.run(self.run_one(sub_task, step_idx))


# ---- 截图辅助 ----


async def _extract_last_screenshot(history: Any, step_idx: int, save_dir: Path) -> str:
    """从 history 里取最后一张截图,存盘 + 返回 base64。

    browser-use 的 history 对象通常有 .screenshots (list of bytes/str)
    或 .last_action.screenshot。优先用 .screenshots,fallback 到空串。
    """
    try:
        shots = getattr(history, "screenshots", None) or []
        if not shots:
            return ""
        # 取最后一张
        raw = shots[-1]
        if isinstance(raw, str):
            # 已经是 base64 或 data URL
            b64 = raw.split(",", 1)[-1] if raw.startswith("data:") else raw
            img_bytes = base64.b64decode(b64)
        else:
            img_bytes = bytes(raw)
            b64 = base64.b64encode(img_bytes).decode()

        # 落盘
        path = save_dir / f"step_{step_idx:03d}_{int(time.time())}.png"
        path.write_bytes(img_bytes)
        return b64
    except Exception:
        return ""


# ---- LangGraph 节点 ----


async def abrowser_agent_node(state: BrowserState) -> dict[str, Any]:
    """LangGraph 异步节点:从 state 取当前步,跑 Browser Agent,返回增量更新。

    配合 LangGraph ainvoke 用法:
        workflow.add_node("a", abrowser_agent_node)
        workflow.add_conditional_edges("a", should_continue, {...})
    """
    sub_tasks = state.get("sub_tasks", [])
    current = state.get("current_step", 0)

    if current >= len(sub_tasks):
        return {"current_step": current, "errors": state.get("errors", []) + ["no more steps"]}

    sub_task = sub_tasks[current]
    print(f"  [browser-node] step {current + 1}/{len(sub_tasks)}: {sub_task[:60]}")

    node = BrowserAgentNode()
    final, screenshot = await node.run_one(sub_task, current)

    success = not final.startswith("[ERROR]")
    error_msg = "" if success else final

    return {
        "current_step": current + 1,
        "screenshots": state.get("screenshots", []) + ([screenshot] if screenshot else []),
        "step_results": state.get("step_results", []) + [final],
        "errors": state.get("errors", []) + ([error_msg] if error_msg else []),
        "retry_counts": state.get("retry_counts", []) + [node.max_retries - 1],
    }


def browser_agent_node(state: BrowserState) -> dict[str, Any]:
    """LangGraph 同步节点:内部用 _run_in_loop 包 abrowser_agent_node。

    自动处理 event loop 嵌套(参考 planning_node 的设计)。
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(abrowser_agent_node(state))

    # 在 loop 里,退到线程
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, abrowser_agent_node(state)).result()


def should_continue(state: BrowserState) -> str:
    """条件边函数:还有步数 + 上一没出错 → 继续;否则 → end。

    配合:
        workflow.add_conditional_edges("browser", should_continue, {
            "browser": "browser",  # 继续下一步
            "end": "extraction",
        })
    """
    current = state.get("current_step", 0)
    total = len(state.get("sub_tasks", []))
    errors = state.get("errors", [])

    if current < total and (not errors or errors[-1] == ""):
        return "browser"
    return "end"


# ---- 便捷:一次性跑完整个计划(给 example / 测试用)----


async def arun_plan(
    sub_tasks: list[str],
    max_steps: int = 10,
    max_retries: int = 3,
) -> dict[str, Any]:
    """串行跑完整份 sub_tasks,适合 example 和集成测试。

    Returns:
        包含 final_result / screenshots / errors 的汇总 dict。
    """
    node = BrowserAgentNode(max_steps=max_steps, max_retries=max_retries)
    results: list[str] = []
    screenshots: list[str] = []
    errors: list[str] = []

    for i, st in enumerate(sub_tasks):
        print(f"\n[{i + 1}/{len(sub_tasks)}] {st}")
        final, shot = await node.run_one(st, i)
        results.append(final)
        if shot:
            screenshots.append(shot)
        if final.startswith("[ERROR]"):
            errors.append(final)
            print(f"  失败: {final[:80]}")
            # 出错是否继续?这里选择继续,但记录错误
        else:
            print(f"  OK: {final[:80]}")

    return {
        "step_results": results,
        "screenshots": screenshots,
        "errors": errors,
        "success_rate": 1 - len(errors) / max(len(sub_tasks), 1),
    }


def run_plan(
    sub_tasks: list[str],
    max_steps: int = 10,
    max_retries: int = 3,
) -> dict[str, Any]:
    """arun_plan 的同步包装。"""
    return asyncio.run(arun_plan(sub_tasks, max_steps, max_retries))
