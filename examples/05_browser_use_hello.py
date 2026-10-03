"""Day 4 Example 1: Browser-Use 最简任务

目标:
    1. 学会用 Agent 跑一个浏览器自动化任务
    2. 看到 LLM 自己驱动浏览器打开、点击、提取数据

核心概念:
    - Agent:一个能"看页面 + 思考 + 行动"的循环
    - task:用自然语言描述要做什么
    - llm:驱动 Agent 决策的大脑

应用场景:
    - "打开 quotes.tosmall.com,把前 3 条名言存成 JSON"
    - LLM 会自己:
        1. 打开页面
        2. 找到名言列表
        3. 提取文字
        4. 输出 JSON

注:
    - 运行时会真的打开 Chrome(默认非 headless),看到 LLM 自己操作
    - 需要 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量
"""

from __future__ import annotations

import asyncio
import json
import os

from browser_use import Agent

from browser_flow.browser import get_browser_profile
from browser_flow.llm import get_llm


async def main() -> None:
    print("=== Browser-Use Example 1: 最简任务(抓名言) ===")

    llm = get_llm()
    print(f"使用 LLM: {llm.model}")

    task = (
        "打开 https://quotes.toscrape.com/ 这个网站,"
        "抓取页面上看到的 **前 3 条名言**("
        "包含名言内容和作者),用 JSON 数组返回,"
        "每条格式: {\"text\": \"...\", \"author\": \"...\"}"
    )
    print(f"任务: {task}")

    agent = Agent(task=task, llm=llm, browser_profile=get_browser_profile())

    # 同步版本(在 LangGraph 节点里要用这个)
    print("\n开始执行 Agent(浏览器会自动打开,你会看到操作过程)...")
    history = await agent.run(max_steps=10)

    # 最终结果在最后一步 done 的 extracted_content 里
    final = history.final_result()
    print("\n=== 最终结果 ===")
    if final:
        print(final)
        # 尝试 JSON 解析(只是演示,不一定成功)
        try:
            parsed = json.loads(final)
            print(f"\n解析后是 {len(parsed)} 条名言")
        except json.JSONDecodeError:
            print("\n(Agent 返回的不是标准 JSON,但有内容)")
    else:
        print("(没有结果)")


if __name__ == "__main__":
    # 检查 API key 是否存在
    if not (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        raise SystemExit(
            "需要 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量\n"
            "示例:set DEEPSEEK_API_KEY=sk-xxx"
        )
    asyncio.run(main())
