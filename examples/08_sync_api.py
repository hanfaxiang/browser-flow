"""BrowserFlow 同步 API 示例。

对比之前 examples/05 — 那次是手写 `async def main() + asyncio.run`,
这次直接 `run_sync(task)` 同步调用,简洁得多。

用法:
    uv run python examples/08_sync_api.py
"""

from __future__ import annotations

import sys

from browser_flow.api import run_sync


def main() -> None:
    # 让 Windows 终端能打印 emoji / 中文
    sys.stdout.reconfigure(encoding="utf-8")

    print("=== BrowserFlow 同步 API: 一行跑完一个浏览器任务 ===")

    task = (
        "打开 https://quotes.toscrape.com/ ,"
        "用一句话告诉我页面上最显眼的那条名言是什么"
    )
    print(f"任务: {task}\n")
    print("执行中...")

    history = run_sync(task)

    print("\n=== 完成 ===")
    print(f"用步数: {history.number_of_steps()}")
    print(f"是否成功: {history.is_successful()}")
    print(f"最终结果: {history.final_result()}")


if __name__ == "__main__":
    main()
