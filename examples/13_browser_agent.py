"""Day 10-11 Example: Browser Agent 单步 + 重试 + 截图。

展示 3 件事:
1. BrowserAgentNode.run_one() 单步执行(带重试)
2. _extract_last_screenshot 截图存档
3. browser_agent_node 作为 LangGraph 节点

注意:
    - 真跑需要 DEEPSEEK_API_KEY / OPENAI_API_KEY + Playwright 浏览器
    - 失败重试用 tenacity 指数退避(1s / 2s / 4s)

跑法: uv run python examples/13_browser_agent.py
"""

from __future__ import annotations

import asyncio
import os

from browser_flow.agents.browser_node import (
    BrowserAgentNode,
    arun_plan,
    browser_agent_node,
)


def banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def demo_single_step() -> None:
    banner("1) BrowserAgentNode 单步执行 + 重试")

    node = BrowserAgentNode(max_steps=5, max_retries=3, headless=True)

    # 单步子任务:让 agent 只做一件事
    sub_task = "打开 https://quotes.toscrape.com/ 抓取页面上**第一条**名言和作者"

    print(f"子任务: {sub_task}")
    print(f"参数: max_steps={node.max_steps}, max_retries={node.max_retries}")

    final, screenshot_b64 = await node.run_one(sub_task, step_idx=0)

    print("\n结果:")
    print(f"  final_result: {final[:200]}")
    print(f"  截图 bytes:   {len(screenshot_b64)} (base64)")
    print("  截图落盘:    screenshots/step_000_*.png")


async def demo_run_plan() -> None:
    banner("2) arun_plan 串行跑多步任务")

    sub_tasks = [
        "打开 https://quotes.toscrape.com/ 抓取第一条名言",
        "点击 'Next' 翻页,抓取新页面第一条名言",
    ]

    result = await arun_plan(sub_tasks, max_steps=5, max_retries=2)

    print("\n汇总:")
    print(f"  步数:    {len(result['step_results'])}")
    print(f"  截图数:  {len(result['screenshots'])}")
    print(f"  错误数:  {len(result['errors'])}")
    print(f"  成功率:  {result['success_rate']:.0%}")

    for i, (r, err) in enumerate(zip(result["step_results"], result["errors"], strict=True), 1):
        prefix = "OK" if not err else "FAIL"
        print(f"  [{i}] {prefix}: {r[:80]}")


async def demo_langgraph_node() -> None:
    banner("3) browser_agent_node 作为 LangGraph 节点")

    # 模拟 LangGraph 把 plan 喂进来
    state: dict = {
        "sub_tasks": ["打开 baidu.com 截图首页"],
        "current_step": 0,
        "screenshots": [],
        "step_results": [],
        "errors": [],
    }

    print(f"输入 state: {state}")
    update = browser_agent_node(state)

    print("\n节点返回:")
    for k, v in update.items():
        if isinstance(v, list):
            print(f"  {k}: list({len(v)} items)")
        else:
            print(f"  {k}: {str(v)[:80]}")


async def main_async() -> None:
    await demo_single_step()
    await demo_run_plan()
    await demo_langgraph_node()


def main() -> None:
    if not (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        raise SystemExit(
            "需要 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量\n"
            "示例: DEEPSEEK_API_KEY=sk-xxx uv run python examples/13_browser_agent.py"
        )
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
