"""Day 9 Example: 多轮反馈 + LangGraph State 接入。

展示 3 件事:
1. aplan() 初次拆解
2. aplan_with_feedback() 根据"再拆细点"重规划
3. planning_node() 作为 LangGraph 节点同步跑

跑法: uv run python examples/12_planning_feedback.py
"""

from __future__ import annotations

import asyncio
import os

from browser_flow.agents.planning import (
    aplan,
    aplan_with_feedback,
    planning_node,
)


def banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def demo_feedback_loop(user_task: str, rounds: list[str]) -> None:
    """跑多轮反馈,展示拆解如何演变。"""
    banner(f"任务: {user_task}")

    current = await aplan(user_task)
    print(f"\n[v0 初版] {len(current.sub_tasks)} 步 / 预估 {current.estimated_steps}")
    for i, s in enumerate(current.sub_tasks, 1):
        print(f"  {i}. {s}")

    for round_idx, feedback in enumerate(rounds, 1):
        current = await aplan_with_feedback(user_task, current, feedback)
        print(f"\n[v{round_idx} 反馈: {feedback!r}]")
        print(f"  {len(current.sub_tasks)} 步 / 预估 {current.estimated_steps}")
        for i, s in enumerate(current.sub_tasks, 1):
            print(f"  {i}. {s}")


async def demo_planning_node() -> None:
    """演示 planning_node 作为 LangGraph 节点用。"""
    banner("LangGraph 节点: planning_node(state)")

    state_in: dict = {"user_task": "打开豆瓣电影 TOP 250 抓评分最高的 10 部电影"}
    result = planning_node(state_in)

    print(f"输入 state: {state_in}")
    print("\n节点返回更新:")
    for k, v in result.items():
        if isinstance(v, list) and len(v) > 3:
            print(f"  {k}: [{len(v)} items]")
        else:
            print(f"  {k}: {v}")


async def main_async() -> None:
    await demo_feedback_loop(
        "打开京东搜索 iPhone 提取前 10 个商品价格",
        rounds=[
            "把'抓取商品'这一步拆细:分别抓标题、价格、评价数",
            "太碎了,把'等待加载'和'抓取'合为一步",
        ],
    )
    await demo_planning_node()


def main() -> None:
    if not (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        raise SystemExit(
            "需要 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量\n"
            "示例: DEEPSEEK_API_KEY=sk-xxx uv run python examples/12_planning_feedback.py"
        )
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
