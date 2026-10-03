"""BrowserFlow 流式 API 示例。

浏览器任务可能要 30 秒-几分钟,UI 必须给用户实时反馈。
流式 API 让你在每一步完成后立刻拿到 AgentStepEvent:
    - 显示"思考中..."
    - 显示"点击了 XX 按钮"
    - 显示"已访问 URL..."

用法:
    uv run python examples/09_streaming_api.py
"""

from __future__ import annotations

import asyncio
import sys

from browser_flow.api import stream


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== BrowserFlow 流式 API: 每步实时输出 ===\n")

    task = "打开 https://quotes.toscrape.com/ ,抓前 2 条名言"
    print(f"任务: {task}\n")

    step_count = 0
    async for event in stream(task):
        step_count += 1
        print(f"[Step {event.step}] {event.action_name} | url={event.url}")
        if event.thought:
            print(f"  💭 {event.thought[:80]}{'...' if len(event.thought) > 80 else ''}")
        if event.done:
            print("\n✅ Agent 判断任务完成")

    print(f"\n=== 总步数: {step_count} ===")


if __name__ == "__main__":
    asyncio.run(main())
