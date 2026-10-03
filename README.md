# BrowserFlow

> 基于 LangGraph 的多 Agent 浏览器自动化平台

让 Agent 像人一样操作浏览器——打开网页、点击按钮、填表、抓数据、做测试,基于视觉理解而非 DOM 选择器,网页改版不影响。

## 核心特性

- 🤖 **Supervisor 多 Agent 协作**:Planning + Browser + Extraction 三 Agent 协同
- 👁️ **多模态视觉理解**:GPT-4o 直接解析页面截图
- 🛡️ **反爬策略**:Stealth 模式 + 人类化操作 + 代理池轮换
- 🔄 **错误恢复**:指数退避重试 + Checkpoint 断点续跑

## 技术栈

| 层级 | 选型 |
| ---- | ---- |
| 编排 | LangGraph |
| 浏览器 | Playwright |
| Agent | Browser-Use |
| 模型 | GPT-4o |
| 依赖 | uv |
| 测试 | pytest + ruff + mypy |

## 快速开始

```bash
# 1. 安装依赖
uv sync

# 2. 装 Playwright 浏览器
playwright install chromium

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY

# 4. 跑示例
uv run python examples/01_playwright_hello.py
```

## 项目结构

```
browserflow/
├── src/browserflow/
│   ├── agents/         # Planning / Browser / Extraction Agent
│   ├── tools/          # 反爬、人类化、代理
│   ├── graph/          # LangGraph StateGraph
│   └── utils/          # 配置、日志
├── tests/              # 单元测试
├── examples/           # 示例代码
├── docs/               # 架构文档与截图
└── data/               # 数据存储
```

## 开发路线

- **Week 1**:基础搭建(Python 环境、Playwright/LangGraph/Browser-Use 三件套 Hello World)
- **Week 2**:多 Agent 化(Planning/Browser/Extraction)
- **Week 3**:反爬 + 工程化(Stealth、Docker、CI)
- **Week 4**:评估 + 文档(Eval Harness、Demo GIF、Release)

## License

MIT