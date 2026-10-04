"""Planning Agent:把用户自然语言任务拆解成可顺序执行的子任务。

为什么需要这一层:
    - 用户说"打开京东搜索 iPhone,提取前 10 个商品价格"
      实际是 N 步浏览器操作的组合(打开 -> 输入 -> 点击 -> 滚动 -> 抓取)。
    - LLM 一次性决策容易跑偏。先拆步骤,再逐步执行,更可控。
    - 拆出来的子任务可以单独 retry / 单独由人审批(HITL)。

设计要点:
    - TaskPlan 是 Pydantic model,字段强校验。
    - 不用 LangChain 的 .with_structured_output()(browser-use 的 ChatModel
      没有这个方法),改走"提示 LLM 输出 JSON -> model_validate_json"。
    - 提供 plan() 同步入口(用 asyncio.run)+ aplan() async 入口。
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, TypedDict

from browser_use.llm.messages import SystemMessage, UserMessage
from pydantic import BaseModel, Field

from browser_flow.llm import get_llm

SYSTEM_PROMPT = """你是浏览器自动化任务规划专家。

你的输入:用户用一句话描述想做的事(通常涉及打开网页、操作、抓数据)。
你的输出:严格 JSON,不要任何额外文字、不要 markdown 围栏。

JSON 结构:
{
  "sub_tasks": ["<第一步>", "<第二步>", ...],
  "estimated_steps": ["05"],
  "rationale": "<一句话说明为什么这么拆>"
}

拆分原则:
1. 每一步是单一浏览器动作(打开 / 点击 / 输入 / 滚动 / 提取 / 关闭)
2. 按时间顺序,从前往后
3. 3-8 步之间,不要拆得过碎("移动鼠标" 这种就不算)
4. 数据提取步骤必须明确:抓什么字段、抓多少条

示例 1:
输入: "打开京东搜索 iPhone,提取前 10 个商品价格"
输出:
{
  "sub_tasks": [
    "打开 jd.com",
    "在搜索框输入 iPhone 并回车",
    "等待搜索结果加载完成",
    "抓取前 10 个商品的标题和价格",
    "保存结果"
  ],
  "estimated_steps": 5,
  "rationale": "搜索型任务,先开站后搜再抓"
}

示例 2:
输入: "登录学校教务系统,导出本学期成绩单"
输出:
{
  "sub_tasks": [
    "打开教务系统登录页",
    "输入学号和密码,点击登录",
    "进入个人主页,找到成绩查询",
    "切换到本学期,展开成绩表",
    "导出或复制成绩单内容"
  ],
  "estimated_steps": 5,
  "rationale": "需要登录 + 多页跳转的复杂流程"
}
"""

REFINITION_PROMPT = """你之前给出的拆解被要求调整。

原任务: {user_task}

原拆解:
{previous_plan}

用户反馈: {feedback}

请根据反馈调整,重新输出严格 JSON(同样的结构)。只输出 JSON,不要其他文字。

调整指南:
- "再拆细点" / "太粗了" : 把合并的步骤拆成多步(单一动作)
- "合并" / "太碎了" : 把连续的小步骤合为一步
- "加上 XX 步" / "漏了 XX" : 在合适位置插入新步骤
- "去掉 XX" : 删除冗余步骤
"""


class TaskPlan(BaseModel):
    """规划结果:子任务列表 + 预估步数 + 简要理由。"""

    sub_tasks: list[str] = Field(
        min_length=1,
        max_length=20,
        description="按顺序排列的子任务,每个是单一浏览器动作",
    )
    estimated_steps: int = Field(
        ge=1,
        le=50,
        description="预估总步数(浏览器操作的总点击/输入次数)",
    )
    rationale: str = Field(
        default="",
        description="为什么这么拆,一句话即可",
    )


def _extract_json(text: str) -> dict[str, Any]:
    """从 LLM 输出里抠 JSON。容忍 ```json ... ``` 围栏和多余前后缀。"""
    if not text:
        raise ValueError("LLM 返回空内容")

    # 1. 围栏
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    # 2. 裸 JSON:找第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"LLM 输出无 JSON 可解析:\n{text[:500]}")
    return json.loads(text[start : end + 1])


async def aplan(user_task: str) -> TaskPlan:
    """把用户任务拆成 TaskPlan。

    Args:
        user_task: 用户的自然语言任务。

    Returns:
        TaskPlan 实例,字段全部校验通过。

    Raises:
        RuntimeError: LLM 不可用或返回内容无法解析为 TaskPlan。
    """
    llm = get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        UserMessage(content=f"用户任务: {user_task}"),
    ]

    # browser-use ChatModel 只有 ainvoke,没有 with_structured_output
    response = await llm.ainvoke(messages)
    content = response.completion if hasattr(response, "completion") else str(response)

    try:
        raw = _extract_json(content)
        return TaskPlan.model_validate(raw)
    except (ValueError, Exception) as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Planning Agent 输出无法解析为 TaskPlan:\n"
            f"  原始输出: {content[:500]}\n"
            f"  错误: {exc}"
        ) from exc


def plan(user_task: str) -> TaskPlan:
    """同步入口:内部用 asyncio.run 包装 aplan()。"""
    return asyncio.run(aplan(user_task))


async def aplan_with_feedback(
    user_task: str,
    previous: TaskPlan,
    feedback: str,
) -> TaskPlan:
    """基于上一版拆解 + 用户反馈再拆一轮。

    用法:
        plan = await aplan("打开京东搜索 iPhone")
        plan2 = await aplan_with_feedback(
            user_task="打开京东搜索 iPhone",
            previous=plan,
            feedback="把'抓取商品'这一步再拆细:进详情页、看价格、看评论、保存",
        )

    Args:
        user_task: 原始用户任务。
        previous: 上一版 TaskPlan。
        feedback: 用户给的具体调整意见。

    Raises:
        RuntimeError: LLM 返回无法解析为 TaskPlan。
    """
    llm = get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        UserMessage(
            content=REFINITION_PROMPT.format(
                user_task=user_task,
                previous_plan=previous.model_dump_json(indent=2),
                feedback=feedback,
            )
        ),
    ]

    response = await llm.ainvoke(messages)
    content = response.completion if hasattr(response, "completion") else str(response)

    try:
        raw = _extract_json(content)
        return TaskPlan.model_validate(raw)
    except (ValueError, Exception) as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Planning Agent 反馈调整后输出无法解析:\n"
            f"  原始输出: {content[:500]}\n"
            f"  错误: {exc}"
        ) from exc


def plan_with_feedback(user_task: str, previous: TaskPlan, feedback: str) -> TaskPlan:
    """同步入口:aplan_with_feedback 的 asyncio.run 包装。"""
    return asyncio.run(aplan_with_feedback(user_task, previous, feedback))


class PlanningState(TypedDict, total=False):
    """LangGraph State 里的 Planning 字段子集。

    用法(给 Day 12 Supervisor 拼图用):
        from typing import TypedDict
        from langgraph.graph import StateGraph

        class FullState(PlanningState, BrowserState, ExtractionState):
            pass

    字段:
        user_task: 原始用户任务(输入)
        sub_tasks: 当前生效的子任务列表(随反馈 / 重规划更新)
        current_step: 当前执行到第几个子任务(0-indexed)
        estimated_steps: 预估总步数
        rationale: 当前拆解的理由
        planning_history: 历次规划结果(给回放 / 调试用)
    """

    user_task: str
    sub_tasks: list[str]
    current_step: int
    estimated_steps: int
    rationale: str
    planning_history: list[dict[str, Any]]


# LangGraph 节点函数:接收 State -> 更新 State


def planning_node(state: PlanningState) -> dict[str, Any]:
    """LangGraph 节点:对 state['user_task'] 做规划,返回更新字典。

    处理嵌套事件循环:
        - 在主线程直接调用 -> 用同步 plan() 包装 asyncio.run
        - 在已有 event loop 里(常见:LangGraph ainvoke / async test)
          -> 走 _plan_sync_threadsafe,避免 RuntimeError

    如果你的图是纯 async,自己写 `async def aplanning_node(state)` 包 aplan()。
    """
    user_task = state.get("user_task", "")
    if not user_task:
        return {"sub_tasks": [], "estimated_steps": 0, "rationale": "no task"}

    plan_obj = _plan_smart(user_task)
    return {
        "user_task": user_task,
        "sub_tasks": plan_obj.sub_tasks,
        "current_step": 0,
        "estimated_steps": plan_obj.estimated_steps,
        "rationale": plan_obj.rationale,
        "planning_history": state.get("planning_history", []) + [plan_obj.model_dump()],
    }


def _plan_smart(user_task: str) -> TaskPlan:
    """优先在当前 event loop 里跑;没在 loop 里就 asyncio.run。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # 不在 loop 里,直接同步跑
        return asyncio.run(aplan(user_task))

    # 在 loop 里,改用 nest_asyncio 或阻塞到后台线程跑
    try:
        import nest_asyncio  # type: ignore[import-not-found]

        nest_asyncio.apply()
        return asyncio.run(aplan(user_task))
    except ImportError:
        # 没装 nest_asyncio,退到线程池
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(lambda: asyncio.run(aplan(user_task))).result()
