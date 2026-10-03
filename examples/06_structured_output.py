"""Day 4 Example 2: Browser-Use 结构化输出

目标:
    1. 学会用 Pydantic 约束 Agent 的输出
    2. 拿到的不是"自然语言答案",而是 typed dict / Pydantic 对象

核心概念:
    - output_model_schema:用 Pydantic BaseModel 描述期望输出结构
    - Agent 完成后会把 JSON 解析成这个 model 的实例
    - 字段名、字段类型强校验(可选字段、List、嵌套对象都行)

应用场景:
    - 抓价格:必须返回 {"price": 123.0, "title": "..."}
    - 抓多条数据:必须返回 [Quote, Quote, ...]
    - 抓联系信息:必须返回 {"email": ..., "phone": ...}
"""

from __future__ import annotations

import asyncio
import os

from browser_use import Agent
from pydantic import BaseModel

from browser_flow.browser import get_browser_profile
from browser_flow.llm import get_llm


class Quote(BaseModel):
    """单条名言:内容和作者。"""

    text: str
    author: str


class QuoteList(BaseModel):
    """名言列表:items 必须是 Quote 数组。"""

    items: list[Quote]


async def main() -> None:
    print("=== Browser-Use Example 2: 结构化输出 ===")

    llm = get_llm()
    print(f"使用 LLM: {llm.model}")

    task = (
        "打开 https://quotes.toscrape.com/ "
        "抓取页面上看到的 **前 3 条名言**"
    )
    print(f"任务: {task}")

    agent = Agent(
        task=task,
        llm=llm,
        browser_profile=get_browser_profile(),
        # 关键:声明期望的输出 schema
        output_model_schema=QuoteList,
    )

    history = await agent.run(max_steps=10)

    print("\n=== 最终 typed dict ===")
    # Agent 把 JSON 解析成 Pydantic 实例
    final = history.final_result()
    if isinstance(final, QuoteList):
        print(f"类型: {type(final).__name__}")
        print(f"名言数: {len(final.items)}")
        for i, q in enumerate(final.items, 1):
            print(f"  {i}. {q.text!r} -- {q.author}")
    elif isinstance(final, dict):
        print("类型: dict, fallback 渲染:")
        print(final)
    else:
        print(f"类型: {type(final).__name__}")
        print(final)


if __name__ == "__main__":
    if not (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        raise SystemExit("需要 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量")
    asyncio.run(main())
