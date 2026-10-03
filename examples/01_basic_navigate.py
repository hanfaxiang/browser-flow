"""Day 2 Example 1: Playwright 基础导航

目标:
    1. 学会 async/await 异步模式
    2. 打开 quotes.toscrape.com,获取页面标题
    3. 保存首张截图

关键 API:
    - async_playwright() 异步上下文管理器
    - chromium.launch(headless=...) 启动浏览器(headless=False 看得到浏览器)
    - browser.new_page() 创建新标签页
    - page.goto(url) 导航到 URL
    - page.title() 获取页面标题
    - page.screenshot(path=...) 截图存档
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

# 输出目录(项目根目录)
SCREENSHOTS_DIR = Path(__file__).resolve().parents[1] / "data" / "screenshots"


async def main() -> None:
    """演示 Playwright 最小用例。"""
    # 确保目录存在
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # async with:进入时启动 playwright,退出时自动清理资源
    async with async_playwright() as p:
        # headless=False 启动有头浏览器(适合调试看效果)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 1. 导航到目标 URL
        url = "https://quotes.toscrape.com"
        print(f"-> 正在打开 {url} ...")
        await page.goto(url, wait_until="domcontentloaded")

        # 2. 获取页面标题
        title = await page.title()
        print(f"-> 页面标题: {title}")

        # 3. 获取当前 URL(确认跳转是否成功)
        current_url = page.url
        print(f"-> 当前 URL: {current_url}")

        # 4. 截图存档
        screenshot_path = SCREENSHOTS_DIR / "01_first_screenshot.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"-> 截图已保存: {screenshot_path}")

        # 5. 关闭浏览器(可选,async with 退出时会自动关闭)
        await browser.close()
        print("-> 完成!")


if __name__ == "__main__":
    asyncio.run(main())
