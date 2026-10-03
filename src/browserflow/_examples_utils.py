"""Day 2 共用工具:名言提取函数。

复用给 examples/02 和 examples/03,避免重复代码。
位于 src/browserflow 内,作为示例工具的一部分(非正式 API)。
"""

from __future__ import annotations

from datetime import datetime

from playwright.async_api import Page
from pydantic import BaseModel, Field


class Quote(BaseModel):
    """单条名言数据结构。"""

    text: str = Field(..., min_length=1, description="名言正文")
    author: str = Field(..., min_length=1, description="作者")
    tags: list[str] = Field(default_factory=list, description="标签列表")


class QuotesPage(BaseModel):
    """一页名言集合。"""

    page_url: str
    total_quotes: int
    quotes: list[Quote]
    crawled_at: str = Field(default_factory=lambda: datetime.now().isoformat())


async def extract_quotes_from_page(page: Page) -> list[Quote]:
    """从当前页提取所有名言。

    quotes.toscrape.com 的 DOM 结构:
        <div class="quote">
            <span class="text">名言文本</span>
            <small class="author">作者</small>
            <div class="tags">
                <a class="tag">标签1</a>
                <a class="tag">标签2</a>
            </div>
        </div>
    """
    quotes: list[Quote] = []

    # locator 模式:惰性求值,必须 await 才能触发实际查询
    quote_elements = page.locator(".quote")
    count = await quote_elements.count()

    for i in range(count):
        quote_el = quote_elements.nth(i)

        text = (await quote_el.locator(".text").text_content()) or ""
        author = (await quote_el.locator(".author").text_content()) or ""

        tag_locator = quote_el.locator(".tag")
        tag_count = await tag_locator.count()
        tags: list[str] = []
        for j in range(tag_count):
            tag_text = (await tag_locator.nth(j).text_content()) or ""
            if tag_text.strip():
                tags.append(tag_text.strip())

        quotes.append(
            Quote(
                text=text.strip().strip('"'),
                author=author.strip(),
                tags=tags,
            )
        )

    return quotes


async def has_next_page(page: Page) -> bool:
    """判断当前页是否有"下一页"按钮。"""
    next_link = page.locator("li.next > a")
    return await next_link.count() > 0
