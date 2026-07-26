import json
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage, HumanMessage, SystemMessage, ToolMessage
)
from typing import TypedDict, Annotated, Literal
import os

load_dotenv()
from aiops_agent.tools import ops_tools

# 使用异步模型
llm = ChatOpenAI(
    model="deepseek-v4-pro",
    api_key=os.getenv("DS_API_KEY"),
    base_url=os.getenv("DS_BASE_URL"),
    temperature=0,
    streaming=True,  # 开启 LLM token 流
)

llm_with_tools = llm.bind_tools(ops_tools)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


async def call_model(state: AgentState, config: dict = None):
    messages = state["messages"]
    response = await llm_with_tools.ainvoke(messages, config=config)
    return {"messages": [response]}


async def call_tools(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    tool_results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        selected_tool = next(t for t in ops_tools if t.name == tool_name)
        result = await selected_tool.ainvoke(tool_args)
        tool_results.append(
            ToolMessage(content=result, tool_call_id=tool_call["id"])
        )
    return {"messages": tool_results}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "end"


def create_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("llm", call_model)
    workflow.add_node("tools", call_tools)
    workflow.set_entry_point("llm")
    workflow.add_conditional_edges("llm", should_continue, {"tools": "tools", "end": END})
    workflow.add_edge("tools", "llm")
    return workflow.compile()


app = FastAPI(title="AIOps 故障排查 Agent")

SYSTEM_PROMPT = (
    "你是一个资深的线上故障排查专家（SRE）。"
    "利用提供的工具（search_logs, get_order_info, get_system_metrics）"
    "帮助用户分析故障原因，并给出明确的根因分析和解决建议。\n\n"
    "分析步骤建议：\n"
    "1. 如果有订单ID，先用 get_order_info 查看订单详情。\n"
    "2. 用 search_logs 搜索相关错误日志。\n"
    "3. 用 get_system_metrics 查看对应服务的指标。\n"
    "4. 综合信息，给出根因分析报告。"
)


async def stream_agent_response(user_input: str):
    """SSE 事件生成器"""
    agent = create_agent_graph()
    initial_state = {
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_input)
        ]
    }

    # 发送开始事件
    yield f"data: {json.dumps({'type': 'status', 'content': 'Agent 开始分析...'}, ensure_ascii=False)}\n\n"

    # 监听所有事件
    async for event in agent.astream_events(initial_state, version="v2"):
        kind = event["event"]

        # 工具开始执行
        if kind == "on_custom_event":
            tool_name = event["name"]
            tool_args = event["data"].get("input", {})
            yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name, 'args': tool_args}, ensure_ascii=False)}\n\n"

        # 工具执行结束
        elif kind == "on_tool_end":
            tool_name = event["name"]
            output = event["data"].get("output", "")
            preview = str(output)[:200] if output else ""
            yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'preview': preview}, ensure_ascii=False)}\n\n"

        # LLM 输出的 token
        elif kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if hasattr(chunk, "content") and chunk.content:
                yield f"data: {json.dumps({'type': 'llm_token', 'content': chunk.content}, ensure_ascii=False)}\n\n"

        # 图运行结束
        elif kind == "on_chain_end" and event["name"] == "LangGraph":
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    yield "data: [DONE]\n\n"


@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "")
    if not user_input:
        return {"error": "消息不能为空"}
    return StreamingResponse(stream_agent_response(user_input), media_type="text/event-stream")


@app.get("/")
async def index():
    return HTMLResponse(open("static/index.html", encoding="utf-8").read())
