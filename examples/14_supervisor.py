"""Day 12-13 Example: Supervisor 三 Agent 串起来。

展示:
    1. 三 Agent 协作:Planning 拆 → Browser 跑 → Extraction 抽
    2. StateGraph 编排(条件边 / 循环)
    3. 真跑用 mocked 的 browser agent(否则太慢)

跑法:
    uv run python examples/14_supervisor.py  # 跑 mock 演示
    uv run python examples/14_supervisor.py --real  # 跑真 Browser(慢)

实跑用 Browser-Use + Playwright,首次跑需 `playwright install chromium`。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel

from browser_flow.agents.supervisor import (
    build_supervisor_graph,
)


class Quote(BaseModel):
    """目标 schema:从 quotes.toscrape.com 抓的名言。"""

    text: str
    author: str


async def run_mock_demo() -> None:
    """Mock 三层 Agent,展示图结构能正确流转。"""
    print("=" * 70)
    print("MOCK 演示:Planning + Browser + Extraction 串图")
    print("=" * 70)

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(
        side_effect=[
            # planning call
            MagicMock(
                completion='{"sub_tasks": ["打开 quotes.toscrape.com 抓前 1 条名言"], '
                '"estimated_steps": 1, "rationale": "静态抓取"}'
            ),
            # extraction call
            MagicMock(
                completion='{"text": "The world as we have created it is...", '
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
                "current_step": 1,
                "step_results": ["raw: <quote>...</quote>"],
                "errors": [],
            },
        )
        as mock_browser,
    ):
        graph = build_supervisor_graph(target_schema=Quote)
        result = graph.invoke({"user_task": "打开 quotes.toscrape.com 抓前 1 条名言"})

    print(f"\n[Planning] user_task:  {result['user_task']}")
    print(f"[Planning] sub_tasks:  {result['sub_tasks']}")
    print(f"[Planning] estimated:  {result['estimated_steps']} 步")
    print(f"[Planning] rationale:  {result['rationale']}")
    print(f"\n[Browser] step_results: {result['step_results']}")
    print(f"[Browser] errors:       {result['errors']}")
    print(f"\n[Extraction] type:      {type(result['extracted']).__name__}")
    print(f"[Extraction] extracted:  {result['extracted_dict']}")
    print(f"[Extraction] error:      {result['extraction_error']!r}")

    assert mock_browser.called, "browser 节点应该被调用"
    print("\n[OK] 三 Agent 协作完成")


async def run_real_demo() -> None:
    """真 Browser 路径(慎用 / 慢)。"""
    print("=" * 70)
    print("REAL 模式:真 Browser-Use + 真 DeepSeek/OpenAI")
    print("=" * 70)

    graph = build_supervisor_graph(target_schema=Quote, use_async_nodes=True)
    initial: dict = {"user_task": "打开 https://quotes.toscrape.com/ 抓取第一条名言和作者"}

    print(f"开始: {initial['user_task']}")
    result = await graph.ainvoke(initial)

    print(f"\n[Planning] sub_tasks:  {result.get('sub_tasks')}")
    print(f"\n[Browser] step_results: {result.get('step_results')}")
    print(f"\n[Extraction] type:      {type(result.get('extracted')).__name__}")
    print(f"[Extraction] extracted:  {result.get('extracted_dict')}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--real",
        action="store_true",
        help="真跑 Browser-Use(慢,需 key + chromium)",
    )
    args = parser.parse_args()

    if args.real:
        if not (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")):
            print("需要 DEEPSEEK_API_KEY / OPENAI_API_KEY", file=sys.stderr)
            sys.exit(1)
        asyncio.run(run_real_demo())
    else:
        asyncio.run(run_mock_demo())


if __name__ == "__main__":
    main()
