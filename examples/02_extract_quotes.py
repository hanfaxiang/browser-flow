"""Day 2 Example 2: 用 Playwright 提取名言并结构化为 JSON

目标:
    1. 学会 locator 选择元素(.quote / .text / .author)
    2. 提取第一页所有名言 + 作者(共 10 条)
    3. 用 Pydantic 定义数据结构,做类型校验
    4. 保存为 JSON 文件

关键 API:
    - page.locator(selector) 返回元素定位器(惰性求值)
    - locator.all() 一次性拿到所有元素
    - await element.text_content() 获取文本
    - locator.count() 计数
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from browserflow._examples_utils import (
    QuotesPage,
    extract_quotes_from_page,
)

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data"


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("-> 打开 quotes.toscrape.com ...")
        await page.goto("https://quotes.toscrape.com", wait_until="domcontentloaded")

        print("-> 提取第一页名言 ...")
        quotes = await extract_quotes_from_page(page)

        # 用 Pydantic 整体打包
        result = QuotesPage(
            page_url=page.url,
            total_quotes=len(quotes),
            quotes=quotes,
        )

        # 保存 JSON
        output_file = OUTPUT_DIR / "quotes_page1.json"
        output_file.write_text(
            result.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"-> 已保存 {result.total_quotes} 条名言到 {output_file}")
        print("\n示例前 3 条:")
        for q in result.quotes[:3]:
            print(f'  "{q.text[:50]}..." — {q.author}')

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
