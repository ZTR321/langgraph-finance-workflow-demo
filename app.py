import os
import re
from typing import Annotated

import gradio as gr
import requests
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict


# ==========================================
# 模块 1：模型与接口配置
# ==========================================
MODEL_NAME = os.getenv(
    "PROJECT_2_MODEL_NAME",
    "gpt-4o-mini",
)
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
PRICE_QUERY_TIMEOUT = 5


def build_llm() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "缺少 OPENAI_API_KEY。请先在环境变量中配置 OpenAI-compatible 接口密钥。"
        )

    return ChatOpenAI(
        model=MODEL_NAME,
        temperature=0,
        api_key=api_key,
        base_url=OPENAI_API_BASE,
    )


llm = build_llm()


# ==========================================
# 模块 2：工具函数区
# ==========================================
def normalize_symbol(symbol: str) -> tuple[str, str]:
    code = str(symbol).strip()
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("请输入 6 位 A 股代码，例如 600519。")

    if code.startswith(("60", "68")):
        return code, "sh"
    if code.startswith(("00", "30")):
        return code, "sz"
    if code.startswith(("43", "83", "87", "88", "92")):
        return code, "bj"

    raise ValueError(f"暂未识别代码 {code} 对应的市场前缀。")


def parse_quote_response(raw_text: str, symbol: str) -> str:
    data_list = raw_text.split("~")
    if len(data_list) <= 3:
        return "数据解析失败，接口返回格式可能已变化。"

    name = data_list[1].strip()
    price = data_list[3].strip()
    if not name or not price:
        return "接口返回了空价格或空名称，暂时无法确认行情。"

    return (
        f"股票名称：{name}\n"
        f"股票代码：{symbol}\n"
        f"最新价格：{price} 元\n"
        "数据说明：基于公开行情接口查询，仅用于 Demo 演示。"
    )


@tool
def get_ashare_price(symbol: str) -> str:
    """查询 A 股股票的最新价格。输入应为 6 位股票代码，例如 '600519'。"""

    try:
        normalized_symbol, market_prefix = normalize_symbol(symbol)
    except ValueError as exc:
        return f"参数错误：{exc}"

    target_code = f"{market_prefix}{normalized_symbol}"
    url = f"https://qt.gtimg.cn/q={target_code}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=PRICE_QUERY_TIMEOUT)
        response.raise_for_status()
        return parse_quote_response(response.text, normalized_symbol)
    except requests.Timeout:
        return "查询超时：行情接口在限定时间内没有返回结果。"
    except requests.RequestException as exc:
        return f"查询失败：外部行情接口异常，详细信息：{exc}"
    except Exception as exc:  # noqa: BLE001
        return f"查询失败：{exc}"


llm_with_tools = llm.bind_tools([get_ashare_price])


# ==========================================
# 模块 3：LangGraph 工作流
# ==========================================
class State(TypedDict):
    messages: Annotated[list, add_messages]
    latest_tool_result: str | None
    draft_response: str | None


def researcher_node(state: State):
    latest_tool_result = state.get("latest_tool_result")
    if state["messages"] and isinstance(state["messages"][-1], ToolMessage):
        latest_tool_result = str(state["messages"][-1].content)

    sys_msg = SystemMessage(
        content=(
            "你是一位谨慎的 A 股研究助理。\n"
            "1. 如果用户明确询问实时股价，优先调用工具查询，不要凭空编价格。\n"
            "2. 如果用户只给股票名称，只有在你对 A 股 6 位代码高度确定时才调用工具；"
            "如果不确定，就明确请用户补充股票代码，避免误查。\n"
            "3. 如果用户问的是通用金融常识、系统介绍或非实时问题，可以直接回答，不必强行调工具。\n"
            "4. 如果刚拿到工具结果，请把结果整合成清晰初稿，避免夸张结论和主观推荐。"
        )
    )
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response], "latest_tool_result": latest_tool_result}


tool_node = ToolNode([get_ashare_price])


def risk_reviewer_node(state: State):
    draft = str(state["messages"][-1].content)
    sys_msg = SystemMessage(
        content=(
            "你是严格但保守的输出审核员。\n"
            "1. 如果草稿中出现“全仓”“梭哈”“买入”“推荐”等明显投资建议表达，"
            "请改写成客观描述，并补上：【合规提示：投资有风险，入市需谨慎。本回答不构成投资建议。】\n"
            "2. 如果草稿本身只是普通事实陈述或系统介绍，请尽量保留原意，不要额外生成废话。\n"
            "3. 不要编造新的价格、研报或结论。"
        )
    )
    review_response = llm.invoke([sys_msg, HumanMessage(content=draft)])
    return {"messages": [review_response], "draft_response": draft}


workflow = StateGraph(State)
workflow.add_node("Researcher", researcher_node)
workflow.add_node("Tools", tool_node)
workflow.add_node("Reviewer", risk_reviewer_node)

workflow.add_edge(START, "Researcher")
workflow.add_conditional_edges(
    "Researcher",
    tools_condition,
    {"tools": "Tools", "__end__": "Reviewer"},
)
workflow.add_edge("Tools", "Researcher")
workflow.add_edge("Reviewer", END)

app = workflow.compile()


# ==========================================
# 模块 4：前端交互
# ==========================================
def build_history_messages(history) -> list:
    messages = []
    for user_msg, assistant_msg in history or []:
        if user_msg:
            messages.append(HumanMessage(content=user_msg))
        if assistant_msg:
            messages.append(AIMessage(content=assistant_msg))
    return messages


def chat_with_agent(message, history):
    try:
        messages = build_history_messages(history)
        messages.append(HumanMessage(content=message))
        final_state = app.invoke(
            {
                "messages": messages,
                "latest_tool_result": None,
                "draft_response": None,
            }
        )
        return final_state["messages"][-1].content
    except Exception as exc:  # noqa: BLE001
        return f"系统异常：{exc}"


demo = gr.ChatInterface(
    fn=chat_with_agent,
    title="金融问答与合规审核 Workflow Demo",
    description=(
        "LangGraph 双角色工作流 | 单工具 A 股价格查询 | "
        "基础输出审核 | Gradio 演示界面"
    ),
    examples=[
        "请问贵州茅台（600519）现在的股价是多少？",
        "中金黄金现在的股价多少？如果你不确定代码就提醒我补充。",
        "你这个系统能做什么？",
    ],
)


if __name__ == "__main__":
    print("正在启动本地 Web Demo ...")
    demo.launch()
