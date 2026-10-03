"""Day 4 测试 1: 结构化输出 schema 验证 + LLM 工厂。

不调真实 LLM、不跑真实浏览器,只测:
    1. Pydantic schema 能正常构造/序列化
    2. LLM 工厂在没 API key 时正确报错
    3. LLM 工厂在有 key 时返回正确类型的实例
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from browser_flow.llm import get_llm


class Quote(BaseModel):
    text: str
    author: str


class QuoteList(BaseModel):
    items: list[Quote]


class Contact(BaseModel):
    email: str | None = None
    phone: str | None = None


def test_quote_schema_constructs_from_dict() -> None:
    q = Quote(text="hello", author="world")
    assert q.text == "hello"
    assert q.author == "world"


def test_quote_list_nests_correctly() -> None:
    payload: dict[str, Any] = {
        "items": [
            {"text": "a", "author": "x"},
            {"text": "b", "author": "y"},
        ]
    }
    parsed = QuoteList.model_validate(payload)
    assert len(parsed.items) == 2
    assert parsed.items[0].author == "x"


def test_contact_schema_optional_fields() -> None:
    """optional 字段允许缺失(浏览器抓不到电话时只返回 email)。"""
    parsed = Contact.model_validate({"email": "a@b.com"})
    assert parsed.email == "a@b.com"
    assert parsed.phone is None


def test_llm_factory_raises_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        get_llm()


def test_llm_factory_picks_deepseek_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """设置 DEEPSEEK_API_KEY 后,factory 应返回 ChatDeepSeek 指向 deepseek-chat。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from browser_use.llm import ChatDeepSeek

    llm = get_llm()
    assert isinstance(llm, ChatDeepSeek)
    assert llm.model == "deepseek-chat"


def test_llm_factory_picks_openai_when_only_openai_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")

    from browser_use.llm import ChatOpenAI as BUChatOpenAI

    llm = get_llm()
    assert isinstance(llm, BUChatOpenAI)
    assert llm.model == "gpt-4o-mini"


def test_llm_factory_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """显式传 model 应该能覆盖默认。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")
    llm = get_llm(model="deepseek-reasoner")
    assert llm.model == "deepseek-reasoner"
