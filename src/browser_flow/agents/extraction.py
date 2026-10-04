"""Extraction Agent:把 Browser Agent 的原始输出清洗成结构化 Pydantic 数据。

报告 Day 12 要点:
    [ ] 用 Pydantic 定义数据结构
    [ ] 实现数据清洗 + 结构化
    [ ] StateGraph 编排三 Agent
    [ ] 跑通第一个完整场景

为什么需要独立 Extraction 层(不直接让 Browser Agent 输出 schema):
    - Browser Agent 的强项是"看图操作",prompt 让它再负责"格式化输出"
      经常 trade-off:格式对的但操作乱了,或操作对但格式错。
    - 分两层:
        * Browser: 打开/点击/输入/截图/把页面文本/JSON 复制回来
        * Extraction: 拿到 raw text + 用户期望的 schema,LLM 清洗填字段
    - Extraction 可单独调 prompt / 用更便宜的 LLM / 接 LLM-as-Judge。

设计:
    - ExtractionTarget[T]:泛型包装 Pydantic model,描述"我要从这个 raw 里抽什么"
    - aextract(raw_text, target) -> T 实例
    - extraction_node(state) -> dict:LangGraph 节点,从 state['last_raw'] + target schema 抽
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, TypeVar

from browser_use.llm.messages import SystemMessage, UserMessage
from pydantic import BaseModel

from browser_flow.llm import get_llm

T = TypeVar("T", bound=BaseModel)


SYSTEM_PROMPT = """你是数据提取专家。

你的输入:
    - raw_text:从浏览器抓回来的原始文本(JSON / HTML / Markdown / 纯文本都可能)
    - schema:目标 Pydantic model 的字段说明(JSON Schema 格式)

你的任务:把 raw_text 里的信息塞进 schema 的字段,严格按字段类型,缺失就 null。

输出:严格 JSON,字段名/类型完全匹配 schema,不要任何额外文字、不要 markdown 围栏。

清洗规则:
1. 价格:去 ¥/$/￥,转 float;负数 / 0 视为缺失(null)
2. 邮箱:只留合法格式,验证 @ 前后
3. 列表:空列表不要返回 [],返回空数组 []
4. 字符串:trim 前后空格
5. 数字:不要带千分位逗号(1234 不是 1,234)
7. 嵌套对象:子字段缺失 → null,不要给 {}
6. 无法判断的字段 → null,不要编造

示例:
raw_text: "商品名: iPhone 15 | 评分: 4.8"
schema: {"title": str, "rating": float | null}
输出: {"title": "iPhone 15", "rating": 4.8}

raw_text: "邮箱: invalid@"
schema: {"email": str | null}
输出: {"email": null}
"""


class ExtractionError(RuntimeError):
    """Extraction Agent 输出无法解析为 target schema。"""


def _extract_json(text: str) -> dict[str, Any]:
    """从 LLM 输出抠 JSON(同 planning 的实现,容忍围栏 / 前缀)。"""
    if not text:
        raise ValueError("LLM 返回空内容")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"无 JSON 可解析: {text[:300]}")
    return json.loads(text[start : end + 1])


async def aextract[T: BaseModel](
    raw_text: str,
    target: type[T],
    extra_instructions: str = "",
) -> T:
    """异步抽取:把 raw_text 按 target schema 清洗成 T 实例。

    Args:
        raw_text: 浏览器抓回来的原始文本。
        target: 目标 Pydantic model 类(必须是 BaseModel 子类)。
        extra_instructions: 用户附加要求,会追加到 user message。

    Returns:
        target 的实例,所有字段校验后。

    Raises:
        ExtractionError: LLM 返回无法解析或 Pydantic 校验失败。
    """
    schema = target.model_json_schema()
    llm = get_llm()

    user_msg = (
        f"目标 schema:\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        f"原始文本:\n```\n{raw_text[:8000]}\n```\n"
    )
    if extra_instructions:
        user_msg += f"\n附加要求: {extra_instructions}\n"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        UserMessage(content=user_msg),
    ]

    response = await llm.ainvoke(messages)
    content = response.completion if hasattr(response, "completion") else str(response)

    try:
        raw = _extract_json(content)
        return target.model_validate(raw)
    except (ValueError, Exception) as exc:  # noqa: BLE001
        raise ExtractionError(
            f"Extraction Agent 输出无法解析为 {target.__name__}:\n"
            f"  raw_text[:200]: {raw_text[:200]}\n"
            f"  LLM 输出: {content[:500]}\n"
            f"  错误: {exc}"
        ) from exc


def extract[T: BaseModel](raw_text: str, target: type[T], extra_instructions: str = "") -> T:
    """同步入口。"""
    return asyncio.run(aextract(raw_text, target, extra_instructions))


# ---- LangGraph 节点集成 ----


async def aextraction_node[T: BaseModel](state: dict[str, Any], target: type[T]) -> dict[str, Any]:
    """LangGraph 异步节点:从 state 取最后一步 raw,按 target schema 抽。

    Args:
        state: LangGraph state,需含 'step_results' 列表。
        target: 期望的 Pydantic 类型。

    Returns:
        dict:含 'extracted'(实例) + 'extracted_dict'(json) + 'extraction_error'。
    """
    step_results = state.get("step_results", [])
    if not step_results:
        return {"extraction_error": "no step_results in state"}

    raw = step_results[-1]
    instance = await aextract(raw, target)
    return {
        "extracted": instance,
        "extracted_dict": instance.model_dump(),
        "extraction_error": "",
    }


def extraction_node[T: BaseModel](state: dict[str, Any], target: type[T]) -> dict[str, Any]:
    """同步 LangGraph 节点包装。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(aextraction_node(state, target))

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, aextraction_node(state, target)).result()


# ---- 便捷:批量抽取(用于多步累积结果)----


async def abatch_extract[T: BaseModel](
    raw_texts: list[str],
    target: type[T],
    extra_instructions: str = "",
) -> list[T]:
    """并发抽多条 raw text。"""
    tasks = [aextract(r, target, extra_instructions) for r in raw_texts]
    return await asyncio.gather(*tasks, return_exceptions=False)


def batch_extract[T: BaseModel](
    raw_texts: list[str],
    target: type[T],
    extra_instructions: str = "",
) -> list[T]:
    """abatch_extract 同步包装。"""
    return asyncio.run(abatch_extract(raw_texts, target, extra_instructions))


# ---- Reusable 目标 schema 示例 ----


class Quote(BaseModel):
    """单条名言 + 作者。"""

    text: str
    author: str


class Product(BaseModel):
    """单条商品(标题 + 价格 + 评分)。"""

    title: str
    price: float | None = None
    rating: float | None = None


class ContactInfo(BaseModel):
    """联系信息。"""

    email: str | None = None
    phone: str | None = None
    address: str | None = None
