# BrowserFlow 项目开发报告

> **LangGraph 浏览器自动化 Agent 项目开发手册**
>
> 项目代号:**BrowserFlow**
>
> 立项日期:2026-10-03
>
> 预计周期:4 周(28 天)
>
> 完成度目标:中等深度(有评估、有工程化、有 Demo)

---

## 目录

1. [项目概述](#一项目概述)
2. [立项背景与价值](#二立项背景与价值)
3. [技术选型](#三技术选型)
4. [架构设计](#四架构设计)
5. [里程碑与任务分解](#五里程碑与任务分解)
6. [核心模块设计](#六核心模块设计)
7. [代码规范](#七代码规范)
8. [测试与评估体系](#八测试与评估体系)
9. [工程化清单](#九工程化清单)
10. [文档与发布](#十文档与发布)
11. [风险与应对](#十一风险与应对)
12. [验收标准](#十二验收标准)
13. [附录:常用命令速查](#十三附录常用命令速查)

---

## 一、项目概述

### 1.1 项目名称

**BrowserFlow** —— 基于 LangGraph 的多 Agent 浏览器自动化平台

### 1.2 一句话简介

> 让 Agent 像人一样操作浏览器——打开网页、点击按钮、填表、抓数据、做测试,基于视觉理解而非 DOM 选择器,网页改版不影响。

### 1.3 核心特性

- 🤖 **Supervisor 多 Agent 协作**:Planning + Browser + Extraction 三 Agent 协同
- 👁️ **多模态视觉理解**:GPT-4o 直接解析页面截图,无需 DOM 选择器
- 🛡️ **反爬策略**:Stealth 模式 + 人类化操作 + 代理池轮换
- 🔄 **错误恢复**:指数退避重试 + Checkpoint 断点续跑 + 验证码自动处理
- 📊 **评估体系**:30+ 条任务自动化测试集 + LangSmith Trace 可视化
- 🐳 **工程化**:Docker 部署 + GitHub Actions CI/CD + pytest 单元测试

### 1.4 目标场景

| 场景 | 用户输入 | Agent 自动完成 |
| ---- | -------- | --------------- |
| 电商价格监控 | "监控京东 iPhone 价格,降价通知我" | 每日定时抓取 → 对比历史 → 微信通知 |
| 自动表单录入 | "把 100 个公司工商信息录入到工商系统" | 读取 Excel → 打开网页 → 自动填写 → 截图存档 |
| 端到端测试 | "测试我们官网的注册流程" | 打开网站 → 注册 → 填表单 → 邮件验证 → 截图报告 |

### 1.5 项目成功指标

```
✅ GitHub 仓库公开,README 完整,能 5 分钟跑起来
✅ 至少 1 个真实场景完整跑通(端到端)
✅ pytest 单元测试覆盖率 ≥ 70%
✅ Eval Harness 30 条任务,任务成功率 ≥ 85%
✅ LangSmith Trace 全程可视化
✅ Docker 镜像能跑
✅ 录制至少 1 段 Demo GIF
✅ 在 GitHub README 列出技术栈、架构图、评估结果
```

---

## 二、立项背景与价值

### 2.1 行业背景

```
传统爬虫痛点:
  · 网页改版 → 选择器失效 → 代码崩
  · JS 动态渲染 → requests 拿不到数据
  · 反爬检测 → 验证码 / 空数据 / IP 封禁
  · 维护成本高 → 一个网站一个脚本

自动化测试痛点:
  · 脚本依赖 DOM,改版易崩
  · 不支持复杂业务逻辑判断
  · 跨页面流程串联困难
```

### 2.2 技术趋势

```
2026 年浏览器 Agent 赛道:
  · Browser-Use GitHub Star 18k+(底层基础设施成熟)
  · GPT-4o / Claude 多模态能力足以识别任意页面
  · LangGraph 成为多 Agent 编排主流框架
  · MCP 协议统一了工具调用标准
  · 越来越多公司把"Agent 操作浏览器"列为正式业务场景
```

### 2.3 对个人的价值

**简历差异化**:
- 90% 候选人 = LangChain + RAG + 向量库
- BrowserFlow = LangGraph + 多模态 + 反爬 + 浏览器自动化
- 面试官:**能聊反爬、视觉模型、Playwright,说明真的做过**

**技能关键词覆盖**(1 个项目 9 个关键词):
LangGraph · LLM · Browser-Use · Playwright · 多模态 · 反爬 · Function Calling · 错误恢复 · Docker

---

## 三、技术选型

### 3.1 技术栈总览

| 层级 | 选型 | 版本 | 选型理由 |
| ---- | ---- | ---- | -------- |
| **编排框架** | LangGraph | ≥0.2 | StateGraph 状态机 + checkpoint + HiTL |
| **底层浏览器** | Playwright | ≥1.40 | 异步原生、自动等待、多浏览器、API 现代 |
| **上层 Agent** | Browser-Use | ≥0.1 | 把 Browser-Use 作为 LangGraph 的工具 |
| **大模型** | GPT-4o | latest | 多模态视觉能力最强 |
| **降本备选** | Qwen-VL / Claude | latest | 预算紧时切换 |
| **数据验证** | Pydantic | ≥2.5 | 类型安全、Schema 校验 |
| **依赖管理** | uv | latest | 快、锁文件、跨平台 |
| **测试** | pytest + pytest-asyncio | latest | 异步测试标配 |
| **部署** | Docker | ≥24 | 跨平台一致 |
| **CI/CD** | GitHub Actions | - | 与 GitHub 集成最好 |
| **监控** | LangSmith | - | Trace 可视化、LLM-as-Judge |
| **反爬** | 自研 Stealth + 代理池 | - | 行业通用做法 |
| **日志** | Loguru | latest | 比 logging 简单太多 |

### 3.2 选型理由详解

#### 为什么 LangGraph 而不是直接用 LangChain Agent?

| 维度 | LangGraph | LangChain Agent |
| ---- | --------- | ----------------- |
| 复杂任务编排 | ⭐⭐⭐⭐⭐ StateGraph | ⭐⭐ ReAct |
| 检查点 / 续跑 | ⭐⭐⭐⭐⭐ MemorySaver | ⭐ 难做 |
| 多 Agent 协作 | ⭐⭐⭐⭐⭐ 原生 | ⭐⭐ 需要手撸 |
| Human-in-the-Loop | ⭐⭐⭐⭐⭐ interrupt | ⭐⭐ |
| 学习曲线 | 中等 | 简单 |

**结论**:LangGraph 是 2026 年多 Agent 编排的事实标准,简历加分高。

#### 为什么 Playwright 而不是 Selenium?

| 维度 | Playwright | Selenium |
| ---- | ---------- | ---------- |
| 异步支持 | ⭐⭐⭐⭐⭐ 原生 asyncio | ⭐ 难做 |
| 自动等待 | ⭐⭐⭐⭐⭐ 内置 | ⭐ 需手动 |
| 多浏览器 | ⭐⭐⭐⭐⭐ Chromium/Firefox/WebKit | ⭐⭐ |
| API 设计 | 现代、链式 | 老旧 |
| 社区活跃度 | 高 | 下降 |

**结论**:Playwright 是 2026 年浏览器自动化首选。

#### 为什么 Browser-Use?

Browser-Use 把"打开浏览器 → 看图 → 决定操作 → 执行"封装成给 LLM 的工具,直接 `from browser_use import Agent` 就能用,省去自己实现 Playwright + 视觉模型的整合代码。

### 3.3 不选的技术(以及为什么)

```
❌ Selenium: 老旧、API 不现代、社区下降
❌ Puppeteer: 仅 Chromium、不支持 Firefox/WebKit
❌ Scrapy: 框架太重、对动态渲染弱
❌ LangChain Agent(单 Agent): 无法做复杂任务编排
❌ AutoGen: 微软风格,社区生态不如 LangGraph
❌ CrewAI: 多 Agent 角色化场景,不适合浏览器自动化
```

---

## 四、架构设计

### 4.1 总体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                       User Interface                         │
│                    (Streamlit / CLI)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Orchestrator                    │
│                  (StateGraph Supervisor)                     │
└──┬────────────────────┬────────────────────┬────────────────┘
   │                    │                    │
   ▼                    ▼                    ▼
┌──────────┐      ┌──────────┐        ┌──────────┐
│ Planning │      │ Browser  │        │Extraction│
│  Agent   │ ───► │  Agent   │ ────► │  Agent   │
└──────────┘      └────┬─────┘        └────┬─────┘
                       │                  │
                       ▼                  ▼
              ┌──────────────────┐  ┌──────────────┐
              │  Browser Layer   │  │ Data Layer   │
              │  Playwright +    │  │ SQLite /     │
              │  Browser-Use +   │  │ JSON /       │
              │  Stealth Mode    │  │ Excel        │
              └────────┬─────────┘  └──────────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  GPT-4o / Claude │
              │  (多模态理解)    │
              └──────────────────┘
```

### 4.2 数据流

```
用户任务
  ↓
Planning Agent(LLM 拆解为 DAG)
  ↓
[打开网页 → 搜索 → 滚动 → 抓取]  ← LangGraph 编排
  ↓
Browser Agent(每步截图 → LLM 决定操作 → Playwright 执行)
  ↓
Extraction Agent(LLM 清洗 + Pydantic 校验)
  ↓
结构化数据(JSON / Excel)
  ↓
保存到 SQLite / 文件
```

### 4.3 状态机设计

```python
class BrowserTaskState(TypedDict):
    """浏览器任务全局状态"""
    # 输入
    user_task: str                    # 用户原始任务

    # 任务分解
    sub_tasks: list[str]              # 拆解后的子任务列表
    current_step: int                 # 当前执行步骤索引
    max_steps: int                    # 最大步数限制

    # 浏览器状态
    page_screenshot: str | None       # base64 截图
    page_url: str                     # 当前页面 URL
    page_html: str | None             # DOM(可选)

    # 数据累积
    extracted_data: dict              # 已抓取数据
    intermediate_results: list[dict]  # 每步结果

    # 错误处理
    errors: list[str]                 # 错误历史
    retry_count: int                  # 当前任务重试次数

    # 控制
    is_done: bool                     # 是否完成
    needs_human_input: bool           # 是否需要人工介入
```

### 4.4 关键决策点(条件路由)

```
START → planning
  ↓
planning → browser(总进入浏览器)
  ↓
browser → [should_continue]
  ├─ 还有子任务 → browser(继续)
  ├─ 出错且可重试 → browser(重试)
  ├─ 出错且不可恢复 → error_handler → END
  ├─ 所有子任务完成 → extraction
  └─ 触发人工介入 → human_input → browser(恢复后)
extraction → END
```

---

## 五、里程碑与任务分解

### 5.1 总体时间线(4 周 = 28 天)

```
Week 1(10/04 - 10/10):基础搭建
Week 2(10/11 - 10/17):多 Agent 化
Week 3(10/18 - 10/24):反爬 + 工程化
Week 4(10/25 - 10/31):评估 + 文档
```

### 5.2 Week 1:基础搭建(Day 1-7)

#### Day 1(周六):环境与工具准备(2-3 小时)

```bash
# 1. 安装 Python 与 uv
# Python 3.11+
uv --version  # 确认 uv 安装

# 2. 建项目目录
mkdir browserflow && cd browserflow
uv init  # 创建 pyproject.toml
uv venv  # 创建虚拟环境
.venv\Scripts\activate  # Windows 激活

# 3. 安装核心依赖
uv add langgraph langchain langchain-openai browser-use playwright
uv add pydantic loguru python-dotenv tenacity
uv add pytest pytest-asyncio pytest-cov --dev

# 4. 安装 Playwright 浏览器
playwright install chromium

# 5. GitHub 建仓库,关联本地
git init
git remote add origin https://github.com/<your-name>/browserflow.git
```

**产出**:
- ✅ 项目目录结构
- ✅ pyproject.toml 依赖锁定
- ✅ GitHub 仓库创建

#### Day 2(周日):Playwright Hello World(3-4 小时)

```python
# examples/01_playwright_hello.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://quotes.toscrape.com")
        title = await page.title()
        print(f"页面标题: {title}")
        # 截图
        await page.screenshot(path="first_screenshot.png")
        await browser.close()

asyncio.run(main())
```

**练习任务**:
- [ ] 打开 quotes.toscrape.com
- [ ] 提取所有名人名言和作者
- [ ] 保存为 JSON 文件
- [ ] 点击"Next"翻页,直到最后一页
- [ ] 截图存档

**产出**:
- ✅ Playwright 跑通,能抓数据
- ✅ 学会 async/await 模式

#### Day 3:LangGraph Hello World(3-4 小时)

```python
# examples/02_langgraph_hello.py
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    counter: int
    messages: list[str]

def increment(state: State):
    return {"counter": state["counter"] + 1,
            "messages": state["messages"] + [f"step {state['counter']}"]}

def should_continue(state: State) -> str:
    return "increment" if state["counter"] < 5 else END

workflow = StateGraph(State)
workflow.add_node("increment", increment)
workflow.add_edge(START, "increment")
workflow.add_conditional_edges("increment", should_continue)

app = workflow.compile()
result = app.invoke({"counter": 0, "messages": []})
print(result)
```

**练习任务**:
- [ ] 跑通上面的代码
- [ ] 加入 MemorySaver checkpoint
- [ ] 加入 Human-in-the-Loop(`interrupt`)
- [ ] 用 LangSmith 监控(注册免费额度)

**产出**:
- ✅ LangGraph 基础会 3 个核心概念(节点、边、checkpoint)

#### Day 4-5:接 Browser-Use(4-5 小时)

```python
# examples/03_browser_use_hello.py
from browser_use import Agent
from langchain_openai import ChatOpenAI
import asyncio

async def main():
    agent = Agent(
        task="打开百度,搜索 'LangGraph',告诉我搜索结果前 3 条的标题",
        llm=ChatOpenAI(model="gpt-4o"),
    )
    result = await agent.run()
    print(f"完成任务: {result.is_done}")
    print(f"最终结果: {result.final_result()}")

asyncio.run(main())
```

**练习任务**:
- [ ] 跑通 Browser-Use 基础 demo
- [ ] 改 task:让它打开京东,搜索 "Python 教程",提取前 5 个商品价格
- [ ] 改 task:让它打开豆瓣电影 TOP 250,提取前 10 部
- [ ] 观察 LangSmith Trace,理解 Agent 的决策路径

**产出**:
- ✅ Browser-Use 能跑通
- ✅ 看到 Agent 是如何决策的(LangSmith Trace)

#### Day 6:项目骨架搭建(3-4 小时)

```
browserflow/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── src/
│   └── browserflow/
│       ├── __init__.py
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── planning.py
│       │   ├── browser.py
│       │   └── extraction.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── stealth.py
│       │   └── humanlike.py
│       ├── graph/
│       │   ├── __init__.py
│       │   └── workflow.py
│       └── utils/
│           ├── __init__.py
│           └── config.py
├── tests/
│   ├── test_planning.py
│   ├── test_browser.py
│   └── test_extraction.py
├── examples/
│   ├── 01_playwright_hello.py
│   ├── 02_langgraph_hello.py
│   └── 03_browser_use_hello.py
├── docs/
│   ├── architecture.png
│   └── eval_results.md
└── data/  # 数据存储
    └── screenshots/
```

#### Day 7:Week 1 收尾

- [ ] 写第一版 README(可简陋,但要能 5 分钟跑起来)
- [ ] 提交代码到 GitHub(`feat: week 1 scaffold`)
- [ ] 复盘:有哪些疑问、卡在哪里、计划调整

---

### 5.3 Week 2:多 Agent 化(Day 8-14)

#### Day 8-9:Planning Agent(4-5 小时)

实现任务分解:
```python
# src/browserflow/agents/planning.py
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel

class TaskPlan(BaseModel):
    """任务分解"""
    sub_tasks: list[str]
    estimated_steps: int

def planning_agent(user_task: str) -> TaskPlan:
    """把用户任务拆解为子任务"""
    llm = ChatOpenAI(model="gpt-4o").with_structured_output(TaskPlan)
    plan = llm.invoke([
        SystemMessage(content="""你是任务规划专家。把用户任务拆为可顺序执行的浏览器操作步骤,例如:
- 打开网站 X
- 在搜索框输入关键词 Y
- 点击搜索按钮
- 滚动加载更多
- 提取价格/标题字段
- 保存到文件

每步独立可执行,返回 list[str]。"""),
        HumanMessage(content=f"用户任务: {user_task}")
    ])
    return plan
```

#### Day 10-11:Browser Agent(5-6 小时)

实现单步浏览器操作:
- [ ] 包装 Browser-Use 为 LangGraph 节点
- [ ] 加入截图存档
- [ ] 加入错误捕获
- [ ] 加入重试逻辑(指数退避)

#### Day 12-13:Extraction Agent + 串起来(5-6 小时)

- [ ] 用 Pydantic 定义数据结构
- [ ] 实现数据清洗 + 结构化
- [ ] StateGraph 编排三 Agent
- [ ] 跑通第一个完整场景

#### Day 14:Week 2 收尾

- [ ] Week 2 demo:跑通"打开 quotes.toscrape.com,提取所有名言"
- [ ] GitHub 提交
- [ ] LangSmith Trace 检查

---

### 5.4 Week 3:反爬 + 工程化(Day 15-21)

#### Day 15-16:StealthBrowser + HumanlikeActions(5-6 小时)

- [ ] 实现 StealthBrowser(去掉 webdriver 标记)
- [ ] 实现 HumanlikeActions(贝塞尔曲线 + 随机延迟)
- [ ] 实现 ProxyRotator(代理池轮换)
- [ ] 测试:在有反爬的网站上跑,看成功率

#### Day 17-18:错误恢复 + Checkpoint(4-5 小时)

- [ ] 接入 tenacity 实现指数退避重试
- [ ] 接入 MemorySaver 实现断点续跑
- [ ] 验证码自动处理(留接口)
- [ ] 测试:故意制造错误,验证恢复机制

#### Day 19-20:Docker + CI/CD(4-5 小时)

- [ ] 写 Dockerfile(基于 python:3.11-slim)
- [ ] 写 docker-compose.yml(可选)
- [ ] GitHub Actions CI:test + lint + build
- [ ] 测试:docker run 能跑起来

#### Day 21:Week 3 收尾

- [ ] 完整跑通一个真实场景
- [ ] 录 Demo GIF

---

### 5.5 Week 4:评估 + 文档(Day 22-28)

#### Day 22-23:Eval Harness(5-6 小时)

- [ ] 设计 30 条评估任务(写在 `data/eval_tasks.jsonl`)
- [ ] 实现自动化评估脚本
- [ ] 接入 LangSmith LLM-as-Judge
- [ ] 跑评估,记录结果到 `docs/eval_results.md`

#### Day 24-25:单元测试 + 覆盖率(4-5 小时)

- [ ] pytest 单元测试覆盖 70%+
- [ ] 集成测试覆盖 1-2 个端到端场景
- [ ] GitHub Actions 自动跑测试

#### Day 26-27:文档(4-5 小时)

- [ ] README 完善(架构图、Demo GIF、技术栈、评估结果)
- [ ] docs/architecture.png(用 draw.io 画)
- [ ] docs/USAGE.md 使用指南
- [ ] docs/DEVELOPMENT.md 开发指南
- [ ] CONTRIBUTING.md(可选)

#### Day 28:发布与庆祝 🎉

- [ ] GitHub 发布 v1.0.0(打 tag)
- [ ] 推上 Twitter / V2EX / 即刻
- [ ] 整理到简历

---

## 六、核心模块设计

### 6.1 模块清单

```
browserflow/
├── agents/          # Agent 实现
│   ├── planning.py      # 任务拆解
│   ├── browser.py       # 浏览器操作
│   └── extraction.py    # 数据提取
├── tools/           # 工具实现
│   ├── stealth.py       # 反检测
│   ├── humanlike.py     # 人类化操作
│   └── proxy.py         # 代理池
├── graph/           # LangGraph 编排
│   └── workflow.py      # StateGraph 定义
├── evaluation/      # 评估
│   ├── tasks.jsonl      # 任务集
│   ├── harness.py       # 评测器
│   └── judges.py        # LLM-as-Judge
└── utils/
    ├── config.py        # 配置管理
    └── logger.py        # 日志
```

### 6.2 关键接口

```python
# 主入口 API
from browserflow import BrowserFlow

bf = BrowserFlow()
result = await bf.run(
    task="打开京东,搜索 iPhone,提取前 10 个商品价格",
    max_steps=20,
    save_to="data/result.json"
)
```

---

## 七、代码规范

### 7.1 Python 风格

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM"]

[tool.mypy]
strict = true
python_version = "3.11"

[tool.black]
line-length = 100
target-version = ["py311"]
```

### 7.2 类型注解

```python
# ✅ 正确:所有函数有类型注解
def parse_price(text: str) -> float:
    """从文本中提取价格"""
    match = re.search(r"¥(\d+\.?\d*)", text)
    return float(match.group(1)) if match else 0.0

# ❌ 错误:无类型注解
def parse_price(text):
    match = re.search(r"¥(\d+\.?\d*)", text)
    return float(match.group(1)) if match else 0.0
```

### 7.3 文档字符串

```python
def planning_agent(user_task: str) -> TaskPlan:
    """把用户任务拆解为可顺序执行的子任务。

    Args:
        user_task: 用户的自然语言任务描述。

    Returns:
        TaskPlan: 包含子任务列表和预估步数。

    Example:
        >>> plan = planning_agent("打开京东搜索 iPhone")
        >>> plan.sub_tasks
        ['打开 jd.com', '在搜索框输入 iPhone', ...]
    """
```

### 7.4 Git 提交规范

```
feat: 新增功能
fix: 修复 bug
docs: 文档更新
refactor: 重构
test: 测试相关
chore: 杂项(配置、依赖等)

示例:
git commit -m "feat: 实现 StealthBrowser 反检测"
git commit -m "fix: 修复 Playwright 超时问题"
git commit -m "docs: 更新 README 增加 Demo"
```

---

## 八、测试与评估体系

### 8.1 单元测试(目标覆盖率 ≥ 70%)

```python
# tests/test_planning.py
import pytest
from browserflow.agents.planning import planning_agent

def test_planning_simple_task():
    plan = planning_agent("打开百度")
    assert len(plan.sub_tasks) >= 1
    assert "百度" in plan.sub_tasks[0]

def test_planning_complex_task():
    plan = planning_agent("打开京东,搜索 iPhone,提取前 10 个商品")
    assert len(plan.sub_tasks) >= 3
```

### 8.2 集成测试

```python
# tests/test_end_to_end.py
import pytest
from browserflow import BrowserFlow

@pytest.mark.asyncio
async def test_extract_quotes():
    bf = BrowserFlow()
    result = await bf.run(
        task="打开 quotes.toscrape.com,提取第一页所有名言",
        max_steps=5
    )
    assert result.is_done
    assert len(result.extracted_data["quotes"]) >= 5
```

### 8.3 Eval Harness(30 条任务)

```jsonl
# data/eval_tasks.jsonl
{"id": 1, "task": "打开百度搜索 'Python'", "expected_keywords": ["Python", "百度"], "max_steps": 5}
{"id": 2, "task": "打开豆瓣电影 TOP 250", "expected_keywords": ["肖申克", "霸王别姬"], "max_steps": 5}
{"id": 3, "task": "打开 quotes.toscrape.com 提取所有名言", "expected_count": 100, "max_steps": 20}
... (共 30 条)
```

```python
# evaluation/harness.py
async def run_eval():
    """跑评估"""
    tasks = load_eval_tasks("data/eval_tasks.jsonl")
    results = []
    for task in tasks:
        result = await run_single_task(task)
        results.append(result)
    return summarize(results)
```

### 8.4 LLM-as-Judge

```python
# evaluation/judges.py
from langchain_openai import ChatOpenAI

def judge_extraction_quality(extracted: str, expected: str) -> float:
    """用 LLM 评估数据提取质量"""
    llm = ChatOpenAI(model="gpt-4o")
    response = llm.invoke([
        SystemMessage(content="你是数据评估专家,评分 0-10"),
        HumanMessage(content=f"提取: {extracted}\n期望: {expected}")
    ])
    return parse_score(response.content)
```

---

## 九、工程化清单

### 9.1 项目配置文件

```
✅ pyproject.toml    # uv 依赖管理
✅ .gitignore        # 忽略 .env、.venv 等
✅ .env.example      # 环境变量模板
✅ Dockerfile        # 容器化
✅ docker-compose.yml(可选)
✅ .github/workflows/ci.yml  # CI/CD
```

### 9.2 .env.example

```bash
OPENAI_API_KEY=sk-xxx
LANGSMITH_API_KEY=lsv2_xxx
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=browserflow

# 代理池(可选)
PROXY_LIST=ip1:port:user:pass,ip2:port:user:pass

# 数据库
DATABASE_URL=sqlite:///./data/browserflow.db
```

### 9.3 Dockerfile

```dockerfile
FROM python:3.11-slim

# 安装 Playwright 依赖
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Playwright 浏览器
RUN playwright install chromium --with-deps

COPY . .
CMD ["uv", "run", "python", "-m", "browserflow"]
```

### 9.4 GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install uv
      - run: uv sync
      - run: playwright install chromium
      - run: uv run ruff check .
      - run: uv run pytest --cov=browserflow --cov-report=xml
      - uses: codecov/codecov-action@v3
```

---

## 十、文档与发布

### 10.1 README 模板

参考项目规划方案中的 README 模板,包含:
- 项目徽章
- 一句话简介
- 核心特性(emoji 列表)
- 架构图
- 快速开始
- 演示 GIF
- 评估结果
- 技术栈
- License

### 10.2 docs/ 目录

```
docs/
├── architecture.png    # 架构图(draw.io)
├── eval_results.md     # 评估结果报告
├── USAGE.md            # 使用指南
├── DEVELOPMENT.md      # 开发指南
└── screenshots/        # 截图
```

### 10.3 发布清单

```
□ GitHub README 写完
□ 录 Demo GIF
□ docs/architecture.png
□ docs/eval_results.md
□ LICENSE(MIT)
□ v1.0.0 release tag
□ 推 Twitter / V2EX / 即刻
□ 更新简历
```

---

## 十一、风险与应对

### 11.1 技术风险

| 风险 | 概率 | 影响 | 应对 |
| ---- | ---- | ---- | ---- |
| OpenAI API 不稳定 | 中 | 高 | 接入 DeepSeek/Qwen 备选 |
| Browser-Use 版本不兼容 | 中 | 中 | 锁版本,可降级 |
| Playwright 浏览器被反爬封 | 高 | 高 | 多 UA + 代理池 + 人类化 |
| LLM 决策错误 | 高 | 中 | 加入重试 + 人工兜底 |
| GPT-4o 视觉识别失败 | 中 | 中 | 加入 DOM 选择器兜底 |

### 11.2 进度风险

| 风险 | 概率 | 影响 | 应对 |
| ---- | ---- | ---- | ---- |
| 4 周时间不够 | 中 | 中 | 缩减功能,优先核心场景 |
| LLM 调用费超预算 | 中 | 中 | 用 Qwen-VL 降本 |
| 评估不达 85% | 中 | 低 | 多调 prompt,延长测试 |
| 代码质量不达标 | 低 | 中 | 严格 ruff + mypy |

### 11.3 资源风险

| 风险 | 应对 |
| ---- | ---- |
| OpenAI Key 余额不足 | 注册新账户 / 用 DeepSeek |
| 没有测试服务器 | 用 quotes.toscrape.com 等公开站 |
| 没时间录 Demo | 用 Peek/ffmpeg 录 5 分钟搞定 |

---

## 十二、验收标准

### 12.1 功能验收(必须 100% 通过)

- [ ] **场景 1**:打开 quotes.toscrape.com,提取第一页所有名言,保存为 JSON ✅
- [ ] **场景 2**:打开 books.toscrape.com,提取第一本书的价格、标题、库存 ✅
- [ ] **场景 3**:打开京东搜索"耳机",提取前 10 个商品价格 ✅(可能被反爬)
- [ ] **场景 4**:打开豆瓣电影 TOP 250,提取前 10 部电影名称 ✅
- [ ] **场景 5**:打开学校教务系统,登录并截图 ✅

### 12.2 工程验收

- [ ] GitHub 仓库公开 ✅
- [ ] README 完整 ✅
- [ ] pytest 单元测试覆盖率 ≥ 70% ✅
- [ ] Docker 镜像能跑 ✅
- [ ] CI/CD 跑通 ✅
- [ ] 录 Demo GIF ✅

### 12.3 评估验收

- [ ] Eval Harness 30 条任务 ✅
- [ ] 任务成功率 ≥ 85% ✅
- [ ] LangSmith Trace 全程可视化 ✅
- [ ] docs/eval_results.md 完整 ✅

### 12.4 简历验收

- [ ] 写好项目经验段 ✅
- [ ] 技术栈、亮点、成果齐全 ✅
- [ ] LangGraph 关键词 ≥ 5 次 ✅

---

## 十三、附录:常用命令速查

### 13.1 uv 命令

```bash
# 创建项目
uv init browserflow

# 添加依赖
uv add langgraph langchain-openai browser-use playwright
uv add pydantic loguru python-dotenv tenacity

# 添加开发依赖
uv add pytest pytest-asyncio pytest-cov --dev

# 同步依赖
uv sync

# 运行
uv run python main.py
uv run pytest
uv run ruff check .
```

### 13.2 Playwright 命令

```bash
# 安装浏览器
playwright install chromium

# 录制脚本(辅助生成代码)
playwright codegen https://example.com

# 调试模式(有头浏览器)
playwright open https://example.com
```

### 13.3 LangGraph 命令

```bash
# 启动 LangSmith Studio(可视化调试)
uv run langgraph dev
```

### 13.4 Docker 命令

```bash
# 构建
docker build -t browserflow:latest .

# 运行
docker run --env-file .env -it browserflow:latest

# 进入容器
docker run --env-file .env -it browserflow:latest /bin/bash
```

### 13.5 Git 命令

```bash
# 提交
git add .
git commit -m "feat: 实现 StealthBrowser"
git push origin main

# 打 tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

---

## 总结

这份开发报告就是 BrowserFlow 项目的**完整工作手册**:
- ✅ **立项清晰**:背景、目标、成功指标明确
- ✅ **任务分解**:4 周 = 28 天,每天具体到小时
- ✅ **架构完整**:从状态机到数据流
- ✅ **工程规范**:代码风格、测试、CI/CD
- ✅ **评估体系**:30 条任务 + LLM-as-Judge
- ✅ **风险预案**:技术 / 进度 / 资源风险全覆盖
- ✅ **验收标准**:功能 / 工程 / 评估 / 简历

**接下来你可以**:
1. 按 Day 1 的清单开始动手(预计 2-3 小时起步)
2. 卡住时回到对应章节找代码模板
3. 每周日做一次复盘,调整下周计划

祝你 4 周后交出漂亮的 BrowserFlow!🚀