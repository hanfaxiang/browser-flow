"""LLM 客户端工厂。

为什么需要这个:
    1. 不在代码里硬编码 API key,统一从环境变量读
    2. 切换 provider 时只改一个地方
    3. 给示例代码一个统一的入口,避免重复样板

设计:
    - get_llm():从环境变量推断 provider
      * DEEPSEEK_API_KEY -> browser_use.llm.ChatDeepSeek
        (browser-use 官方给的 DeepSeek 客户端,比 ChatOpenAI 兼容模式更稳)
      * OPENAI_API_KEY   -> browser_use.llm.ChatOpenAI
        (browser-use 包装的 OpenAI 客户端)
    - 都没有 -> 抛 RuntimeError(明确告诉用户怎么修)
"""

from __future__ import annotations

import os

from browser_use.llm import ChatDeepSeek, ChatOpenAI


def get_llm(model: str | None = None, temperature: float = 0.0):
    """返回统一配置的 LLM 客户端。

    Args:
        model:模型名。None 时按 provider 选默认:
            - DeepSeek -> "deepseek-chat"
            - OpenAI   -> "gpt-4o-mini"
        temperature:LLM 采样温度。浏览器任务推荐 0(确定性)。

    Returns:
        browser-use 兼容的 ChatModel(有 .provider 属性)
    """
    # 优先 DeepSeek(便宜 + 中文好 + browser-use 官方支持)
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if deepseek_key:
        return ChatDeepSeek(
            model=model or "deepseek-chat",
            api_key=deepseek_key,
            temperature=temperature,
        )

    # 退到 OpenAI(用 browser-use 自己的 ChatOpenAI,不是 langchain 的)
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        base_url = os.environ.get("OPENAI_BASE_URL") or None
        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            api_key=openai_key,
            base_url=base_url,
            temperature=temperature,
        )

    raise RuntimeError(
        "未配置 LLM API key。请设置环境变量 DEEPSEEK_API_KEY 或 OPENAI_API_KEY"
    )
