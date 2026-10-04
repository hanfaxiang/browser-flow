"""Extraction Agent 单元测试。"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from browser_flow.agents.extraction import (
    ContactInfo,
    Product,
    Quote,
    _extract_json,
    aextract,
    batch_extract,
    extract,
    extraction_node,
)

# ---- 纯逻辑 ----


class TestExtractJson:
    def test_fenced(self) -> None:
        text = '```json\n{"a": 1}\n```'
        assert _extract_json(text) == {"a": 1}

    def test_bare(self) -> None:
        assert _extract_json('"prefix" {"k": "v"} "suffix"') == {"k": "v"}

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            _extract_json("")

    def test_no_json_raises(self) -> None:
        with pytest.raises(ValueError):
            _extract_json("我答不出来")


# ---- Mock 端到端 ----


class _FakeLLM:
    """模拟 browser-use ChatModel 的 ainvoke。"""

    def __init__(self, content: str) -> None:
        self._content = content
        self.call_count = 0

    async def ainvoke(self, messages: list) -> MagicMock:
        self.call_count += 1
        resp = MagicMock()
        resp.completion = self._content
        return resp


class TestExtractMocked:
    @pytest.mark.asyncio
    async def test_quote_extraction(self) -> None:
        llm = _FakeLLM(
            '{"text": "Stay hungry, stay foolish.", "author": "Steve Jobs"}'
        )
        with patch("browser_flow.agents.extraction.get_llm", return_value=llm):
            quote = await aextract(
                "名言: 'Stay hungry, stay foolish.' -- Steve Jobs",
                Quote,
            )

        assert isinstance(quote, Quote)
        assert quote.text == "Stay hungry, stay foolish."
        assert quote.author == "Steve Jobs"

    @pytest.mark.asyncio
    async def test_product_with_nulls(self) -> None:
        """LLM 返回 null 应该被接受为 None。"""
        llm = _FakeLLM('{"title": "iPhone 15", "price": 5999.0, "rating": null}')
        with patch("browser_flow.agents.extraction.get_llm", return_value=llm):
            p = await aextract("iPhone 15 售价 5999", Product)

        assert p.title == "iPhone 15"
        assert p.price == 5999.0
        assert p.rating is None

    @pytest.mark.asyncio
    async def test_fenced_json(self) -> None:
        llm = _FakeLLM('```json\n{"text": "x", "author": "y"}\n```')
        with patch("browser_flow.agents.extraction.get_llm", return_value=llm):
            q = await aextract("x -- y", Quote)

        assert q.text == "x"
        assert q.author == "y"

    @pytest.mark.asyncio
    async def test_invalid_json_raises(self) -> None:
        from browser_flow.agents.extraction import ExtractionError

        llm = _FakeLLM("LLM 编不出 JSON 就摆烂")
        with (
            patch("browser_flow.agents.extraction.get_llm", return_value=llm),
            pytest.raises(ExtractionError, match="无法解析"),
        ):
            await aextract("any", Quote)

    @pytest.mark.asyncio
    async def test_schema_mismatch_raises(self) -> None:
        """JSON 解析成功但 Pydantic 校验失败。"""
        from browser_flow.agents.extraction import ExtractionError

        # Quote 必须有 text/author,这里故意给 price
        llm = _FakeLLM('{"price": 99}')
        with (
            patch("browser_flow.agents.extraction.get_llm", return_value=llm),
            pytest.raises(ExtractionError),
        ):
            await aextract("any", Quote)


# ---- 同步 / batch / node ----


def test_extract_sync_wrapper() -> None:
    llm = _FakeLLM('{"text": "t", "author": "a"}')
    with patch("browser_flow.agents.extraction.get_llm", return_value=llm):
        q = extract("t -- a", Quote)

    assert isinstance(q, Quote)


def test_batch_extract() -> None:
    llm = _FakeLLM('{"text": "t", "author": "a"}')
    with patch("browser_flow.agents.extraction.get_llm", return_value=llm):
        results = batch_extract(["r1", "r2", "r3"], Quote)

    assert len(results) == 3
    assert all(isinstance(r, Quote) for r in results)


def test_extraction_node_uses_last_result() -> None:
    """LangGraph 节点:取 step_results 最后一条,按 target 抽。"""
    llm = _FakeLLM('{"text": "t", "author": "a"}')
    with patch("browser_flow.agents.extraction.get_llm", return_value=llm):
        state: dict = {"step_results": ["ignored", "real: t -- a"]}
        update = extraction_node(state, Quote)

    assert isinstance(update["extracted"], Quote)
    assert update["extracted_dict"] == {"text": "t", "author": "a"}
    assert update["extraction_error"] == ""


def test_extraction_node_empty_state() -> None:
    """空 state 应返回错误标记,不崩。"""
    update = extraction_node({}, Quote)
    assert "extraction_error" in update


# ---- 真 LLM 端到端(需要 key)----


HAS_KEY = bool(os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY"))


@pytest.mark.skipif(not HAS_KEY, reason="需要 LLM API key")
class TestExtractionEndToEnd:
    @pytest.mark.asyncio
    async def test_real_quote_extraction(self) -> None:
        quote = await aextract(
            "Here is a quote: 'To be or not to be, that is the question.' "
            "-- William Shakespeare",
            Quote,
        )
        assert isinstance(quote, Quote)
        assert "be or not to be" in quote.text.lower() or "to be" in quote.text.lower()
        assert "shakespeare" in quote.author.lower()

    @pytest.mark.asyncio
    async def test_real_contact_extraction(self) -> None:
        info = await aextract(
            "联系我们: support@example.com, 电话 400-123-4567, "
            "地址北京市朝阳区 xx 大厦",
            ContactInfo,
        )
        assert info.email == "support@example.com"
