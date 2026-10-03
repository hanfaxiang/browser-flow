"""Day 2 Example 4: 反爬前置知识 - 检查 webdriver 标记

目标:
    1. 学会 evaluate() 在浏览器内执行任意 JS
    2. 检查 navigator.webdriver(自动化脚本的标志,反爬会检查这个)
    3. 切换网站到 books.toscrape.com 练手
    4. 为 Day 15 的 StealthBrowser 埋下伏笔

关键 API:
    - page.evaluate(js_string) 在页面上下文执行 JS,返回值 await 后拿到
    - page.goto(url) 支持任意 URL,验证多站点切换

为什么重要?
    网站可以用 navigator.webdriver === true 判断你是爬虫 → 拦截
    Playwright 默认会让 webdriver=True**, Day 15 我们要让它变成 False
"""

from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright


async def check_webdriver_marker(page) -> dict:
    """检查浏览器自动化特征。"""
    # 在页面里执行 JS,获取多个反爬检测点
    result = await page.evaluate(
        """() => ({
            webdriver: navigator.webdriver,
            user_agent: navigator.userAgent,
            languages: navigator.languages,
            plugins_count: navigator.plugins.length,
            languages_full: Object.getOwnPropertyDescriptor(
                Navigator.prototype, 'languages'
            ),
            chrome_runtime: typeof window.chrome !== 'undefined'
                && typeof window.chrome.runtime !== 'undefined',
        })"""
    )
    return result


async def main() -> None:
    async with async_playwright() as p:
        # 关键差异测试:有头 vs 无头
        for headless in (False, True):
            print(f"\n=== headless={headless} ===")
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()

            print("-> 打开 bot.sannysoft.com 反爬测试页 ...")
            try:
                await page.goto(
                    "https://bot.sannysoft.com",
                    wait_until="domcontentloaded",
                    timeout=15000,
                )
            except Exception as e:
                print(f"  (该网站可能访问慢,跳过:{type(e).__name__})")
                await browser.close()
                continue

            print("-> 检查 navigator.webdriver ...")
            marker = await check_webdriver_marker(page)

            webdriver_status = (
                "[!] 是(被反爬识别为脚本)" if marker["webdriver"]
                else "[OK] 否(看起来像真实浏览器)"
            )
            print(f"  navigator.webdriver = {marker['webdriver']}  {webdriver_status}")
            print(f"  plugins 数量: {marker['plugins_count']}")
            print(f"  languages: {marker['languages']}")

            # 顺便练手:切换到 books.toscrape.com
            print("\n-> 切换到 books.toscrape.com ...")
            await page.goto(
                "https://books.toscrape.com", wait_until="domcontentloaded"
            )
            title = await page.title()
            print(f"  页面标题: {title}")
            book_count = await page.locator(".product_pod").count()
            print(f"  页面书籍数: {book_count}")

            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
