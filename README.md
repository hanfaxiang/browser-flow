# BrowserFlow

> 让 LLM 替你操作浏览器 — 5 分钟跑起来

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

BrowserFlow 是基于 [browser-use](https://github.com/browser-use/browser-use) + LangGraph 的浏览器自动化框架。提供同步 / 异步 / 流式三件套 API,内置 LLM、浏览器反指纹、截图存档。

## 5 分钟跑起来

### 1. 安装

```bash
git clone <repo-url> browser-flow
cd browser-flow
uv sync
```

### 2. 配置 LLM

复制环境变量模板并填入你的 key:

```bash
cp .env.example .env
# 编辑 .env,填 OPENAI_API_KEY / ANTHROPIC_API_KEY 等
```

### 3. 跑第一个示例

```bash
uv run python examples/05_browser_use_hello.py
```

会打开一个无头浏览器去 quotes.toscrape.com 抓名言,几秒后打印结果。

## 三种用法

### 同步(最常用,像普通 Python 函数)

```python
from browser_flow.api import run_sync

history = run_sync("打开 quotes.toscrape.com 抓 3 条名言")
print(history.final_result())  # 直接拿最终结果
```

### 异步(给 FastAPI / 异步服务用)

```python
import asyncio
from browser_flow.api import arun

history = asyncio.run(arun("抓 quotes.toscrape.com 前 5 条名言"))
```

### 流式(给 UI 用,实时显示每步)

```python
import asyncio
from browser_flow.api import stream

async def main():
    async for event in stream("打开 quotes.toscrape.com"):
        print(f"[Step {event.step}] {event.action_name} | {event.url}")
        if event.done:
            print("完成")

asyncio.run(main())
```

## 示例清单

| # | 文件 | 学什么 |
|---|------|--------|
| 01 | `examples/01_basic_navigate.py` | Playwright 直接打开页面 |
| 02 | `examples/02_extract_quotes.py` | 抓多条数据 + 分页 |
| 03 | `examples/03_pagination.py` | 翻页逻辑 |
| 04 | `examples/04_stealth_check.py` | 反指纹 / 隐身测试 |
| 05 | `examples/05_browser_use_hello.py` | browser-use 第一行 |
| 06 | `examples/06_structured_output.py` | Pydantic 结构化输出 |
| 07 | `examples/07_browser_use_in_langgraph.py` | LangGraph 状态图 |
| 08 | `examples/08_sync_api.py` | **同步 API** |
| 09 | `examples/09_streaming_api.py` | **流式 API** |
| 10 | `examples/10_streamlit_app.py` | **Web UI(Streamlit)** |

## Web UI 启动

```bash
uv run streamlit run examples/10_streamlit_app.py
```

浏览器打开 http://localhost:8001 即可。

## 切换 LLM

默认使用 `OPENAI_API_KEY`,改模型只需在 `.env`:

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini   # 可选,默认 gpt-4o
```

或换成 Claude / DeepSeek 等(见 `src/browser_flow/llm.py`)。

## 项目结构

```
browser-flow/
├── src/browser_flow/
│   ├── __init__.py
│   ├── api.py        # 同步/异步/流式 API
│   ├── llm.py        # LLM 工厂
│   ├── browser.py    # 浏览器配置(沙箱/反指纹)
│   └── graph.py      # LangGraph 节点(可选)
├── examples/         # 10 个示例
├── tests/            # pytest 单测
└── BrowserFlow项目开发报告.md   # 项目规划文档
```

## 开发

```bash
uv run pytest           # 跑测试
uv run ruff check       # 代码风格
uv run python examples/XX_your_xxx.py   # 跑某个示例
```

## License

MIT