"""BrowserFlow Web UI(Streamlit)。

一个简单可视化的浏览器任务界面:
    - 输入任务描述
    - 实时显示每步 action + 当前 URL
    - 最终结果显示在折叠面板里
    - 支持自定义 LLM 模型

为什么用 Streamlit:
    - 1 行启动 web 界面
    - 自带 st.spinner / st.write 流式更新
    - 适合 Demo / 个人工具,不适合生产(无状态/无鉴权)

启动:
    uv run streamlit run examples/10_streamlit_app.py
"""

from __future__ import annotations

import asyncio
import sys

import streamlit as st

from browser_flow.api import BrowserFlowError, stream


def _run_stream(task: str, status_box, log_box) -> None:
    """在 Streamlit 里同步消费异步生成器。

    Streamlit 是同步的脚本模型;用 asyncio.run 跑一个 coroutine 即可。
    每收到一个 event 用 st.write 写到 log_box 里,实现"实时刷"。
    """
    lines: list[str] = []

    async def _consume() -> None:
        async for event in stream(task):
            line = f"**Step {event.step}** · `{event.action_name}` · {event.url or '-'}"
            if event.thought:
                line += f"\n  > {event.thought[:120]}"
                if len(event.thought) > 120:
                    line += "..."
            lines.append(line)
            log_box.markdown("\n\n".join(lines))
            if event.done:
                status_box.success("任务完成")

    try:
        with status_box.status("Agent 跑起来了..."):
            asyncio.run(_consume())
    except BrowserFlowError as e:
        status_box.error(f"运行失败: {e}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    st.set_page_config(
        page_title="BrowserFlow",
        page_icon="🌐",
        layout="centered",
    )
    st.title("🌐 BrowserFlow")
    st.caption("一行指令,让 LLM 替你操作浏览器")

    # 输入区
    task = st.text_area(
        "任务描述",
        value="打开 https://quotes.toscrape.com/ ,抓前 2 条名言",
        height=80,
        help="用自然语言描述你想让浏览器做什么",
    )

    run_btn = st.button("🚀 运行", type="primary")

    # 状态 + 日志输出区
    status_box = st.empty()
    log_box = st.empty()

    if run_btn:
        if not task.strip():
            st.warning("请输入任务")
        else:
            _run_stream(task.strip(), status_box, log_box)


if __name__ == "__main__":
    main()
