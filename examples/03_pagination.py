"""Day 2 Example 3: 自动翻页,提取所有名言(共 10 页 100 条)

目标:
    1. 学会点击 "Next" 按钮翻页
    2. 学会用 try/except 处理翻到最后一页时按钮消失
    3. 学会 expect_navigation 自动等待页面跳转

关键 API:
    - page.locator("li.next > a").click() 点击翻页
    - async with page.expect_navigation(): 等待导航完成
    - locator.count() 判断元素是否存在
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import TimeoutError as PWTimeout
from playwright.async_api import async_playwright

from browserflow._examples_utils import (
    QuotesPage,
    extract_quotes_from_page,
    has_next_page,
)

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data"


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("-> 打开 quotes.toscrape.com 开始翻页 ...")
        await page.goto(
            "https://quotes.toscrape.com", wait_until="domcontentloaded"
        )

        all_quotes: list = []
        page_num = 1
        max_pages = 20  # 安全上限,防止意外死循环

        while page_num <= max_pages:
            print(f"-> 第 {page_num} 页 ...")

            quotes = await extract_quotes_from_page(page)
            all_quotes.extend(quotes)

            # 判断是否有下一页
            if not await has_next_page(page):
                print(f"  已到最后一页,共 {page_num} 页")
                break

            # 点击 "Next" 按钮,等导航完成
            try:
                async with page.expect_navigation():
                    await page.locator("li.next > a").click()
                page_num += 1
            except PWTimeout:
                print("  等待页面加载超时,提前结束")
                break

        # 打包 + 保存
        result = QuotesPage(
            page_url="https://quotes.toscrape.com",
            total_quotes=len(all_quotes),
            quotes=all_quotes,
        )
        output_file = OUTPUT_DIR / "quotes_all.json"
        output_file.write_text(
            result.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"\n-> 总计提取 {result.total_quotes} 条名言,共 {page_num} 页")
        print(f"-> 已保存到 {output_file}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
