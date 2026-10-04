# BrowserFlow

> 让 LLM 替你操作浏览器 — 5 分钟跑起来

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-79%20passed-brightgreen)]()
[![Ruff](https://img.shields.io/badge/ruff-passed-brightgreen)]()

BrowserFlow 是基于 [browser-use](https://github.com/browser-use/browser-use) + LangGraph 的浏览器自动化框架。三层 API(同步/异步/流式)+ 三 Agent 协作(Planning/Browser/Extraction)+ 完整测试覆盖。

## 5 分钟跑起来

### 1. 安装

```bash
git clone <repo-url> browser-flow
cd browser-flow
uv sync
playwright install chromium  # 真跑 Browser 时需要
```

### 2. 配置 LLM

```bash
cp .env.example .env
# 编辑 .env,填 DEEPSEEK_API_KEY(默认)或 OPENAI_API_KEY
```

### 3. 跑第一个示例

```bash
uv run python examples/05_browser_use_hello.py   # browser-use 单步
uv run python examples/14_supervisor.py          # Planning+Browser+Extraction 三层(mock)
uv run python examples/14_supervisor.py --real    # 真 Browser(慢)
```

## 两种用法

### A. 简单 API(类似普通函数)

```python
from browser_flow.api import run_sync

history = run_sync("打开 quotes.toscrape.com 抓 3 条名言")
print(history.final_result())
```

异步 / 流式见 `src/browser_flow/api.py`(`run_async` / `stream_task`)。

### B. Supervisor 图(三 Agent 编排)

```python
from pydantic import BaseModel
from browser_flow.agents.supervisor import build_supervisor_graph

class Quote(BaseModel):
    text: str
    author: str

graph = build_supervisor_graph(target_schema=Quote)
result = graph.invoke({"user_task": "打开 quotes.toscrape.com 抓第一条名言"})
print(result["extracted_dict"])  # {'text': '...', 'author': '...'}
```

图结构:
```
START -> planning -> browser(条件边:有步数继续 / 完成 -> extraction) -> END
```

## 架构

```
用户任务
   ↓
Planning Agent       ← 拆解成 3-8 步子任务(TaskPlan Pydantic)
   ↓
Browser Agent 节点   ← LangGraph 节点,browser-use + tenacity 重试 + 截图存档
   ↓ 循环(should_continue 路由)
Extraction Agent     ← 清洗 raw → 目标 Pydantic schema
   ↓
结构化数据(JSON / Pydantic 实例)
```

### 三个 Agent 模块
| 模块 | 文件 | 职责 |
|---|---|---|
| Planning | `src/browser_flow/agents/planning.py` | 拆任务 + 多轮反馈 + LangGraph 节点 |
| Browser | `src/browser_flow/agents/browser_node.py` | 跑单步 + 重试 + 截图 + LangGraph 节点 |
| Extraction | `src/browser_flow/agents/extraction.py` | 清洗 raw → schema + 批量抽取 |

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
| 11 | `examples/11_planning_agent.py` | Planning Agent 拆任务 |
| 12 | `examples/12_planning_feedback.py` | 多轮反馈 + LangGraph 节点 |
| 13 | `examples/13_browser_agent.py` | Browser 单步 + 重试 + 截图 |
| 14 | `examples/14_supervisor.py` | **三 Agent Supervisor 图** |

## Web UI 启动

```bash
uv run streamlit run examples/10_streamlit_app.py
```

浏览器打开 http://localhost:8001 即可。

## 切换 LLM

默认优先 `DEEPSEEK_API_KEY`(便宜 + 中文好),`OPENAI_API_KEY` 兜底。见 `src/browser_flow/llm.py`。

## 测试

```bash
uv run pytest           # 79 tests, ~13s
uv run pytest -v        # 看每个测试名
uv run pytest -k agent  # 只跑带 agent 的测试
uv run ruff check src examples tests   # ruff 风格检查
```

当前:**79/79 passed**,ruff All checks passed。

## 项目结构

```
browser-flow/
├── src/browser_flow/
│   ├── __init__.py
│   ├── api.py                       # 同步/异步/流式 API
│   ├── llm.py                       # LLM 工厂
│   ├── browser.py                   # 浏览器配置
│   └── agents/
│       ├── planning.py              # Planning Agent + 多轮反馈
│       ├── browser_node.py          # Browser Agent + 重试 + 截图
│       ├── extraction.py            # Extraction Agent + 清洗
│       └── supervisor.py            # StateGraph 串三 Agent
├── examples/                        # 14 个示例
├── tests/                           # 79 个测试
└── BrowserFlow项目开发报告.md        # 项目规划文档
```

## 开发进度

| 周 | Day | 状态 |
|---|---|---|
| Week 1 | Day 1-7 基础搭建 | ✅ |
| Week 2 | Day 8-13 三 Agent 协作 | ✅ |
| Week 2 | Day 14 收尾(本 commit) | ✅ |
| Week 3 | Day 15-21 Stealth + 工程化 | ⏳ |
| Week 4 | Day 22-28 Eval + 文档 | ⏳ |

## License

MIT