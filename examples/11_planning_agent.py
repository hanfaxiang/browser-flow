"""Day 8 Example: Planning Agent — 把用户任务拆成可执行子任务。

适用场景:
    - 调试 prompt 看 LLM 拆得对不对
    - 评估不同任务的可拆解性
    - 给 Week 2 的 Supervisor Agent 做前置验证

跑法: uv run python examples/11_planning_agent.py
"""

from __future__ import annotations

import asyncio
import os

from browser_flow.agents.planning import TaskPlan, aplan

DEMO_TASKS = [
    "打开 quotes.toscrape.com 抓取第一页所有名言和作者",
    "打开京东搜索 iPhone,提取前 10 个商品标题和价格,保存为 JSON",
    "登录学校教务系统,导出本学期成绩单",
    "打开豆瓣电影 TOP 250,提取评分最高的 10 部电影",
    "在 GitHub 搜索 browser-use 仓库,star 数前 5 个",
]


def render(task: str, idx: int, plan_obj: TaskPlan | Exception) -> None:
    print(f"\n{'=' * 70}")
    print(f"[{idx}] 任务: {task}")
    print("-" * 70)
    if isinstance(plan_obj, Exception):
        print(f"[!] 失败: {plan_obj}")
        return

    print(f"预估步数: {plan_obj.estimated_steps}")
    print(f"理由: {plan_obj.rationale or '(无)'}")
    print(f"子任务数: {len(plan_obj.sub_tasks)}")
    print("\n拆分结果:")
    for i, step in enumerate(plan_obj.sub_tasks, 1):
        print(f"  {i}. {step}")


async def plan_one(task: str) -> TaskPlan | Exception:
    try:
        return await aplan(task)
    except RuntimeError as exc:
        return exc


async def main_async() -> None:
    # 并发跑 5 个任务,展示规划能力
    results = await asyncio.gather(
        *(plan_one(t) for t in DEMO_TASKS), return_exceptions=False
    )
    for i, (t, r) in enumerate(zip(DEMO_TASKS, results, strict=True), 1):
        render(t, i, r)


def main() -> None:
    if not (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        raise SystemExit(
            "需要 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量\n"
            "示例: DEEPSEEK_API_KEY=sk-xxx uv run python examples/11_planning_agent.py"
        )
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
