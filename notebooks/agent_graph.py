# ---------- 定义工具 ----------
import os
from datetime import datetime
from typing import TypedDict, Sequence, Annotated, Literal

import requests
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import add_messages, StateGraph, END
from pydantic import BaseModel, Field


load_dotenv()


@tool
def get_weather(city: str) -> str:
    """获取指定城市的实时天气信息。参数 city 是城市名称，如 '杭州' 或 'Beijing'。"""
    try:
        url = f"https://wttr.in/{city}?format=%C+%t+%w"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return f'{city}天气情况：{response.text.strip()}'
        else:
            return f'无法获取{city}的天气'
    except Exception as e:
        return f'查询天气失败：{e}'


@tool
def get_current_time():
    """获取当前的日期和时间，不需要任何参数。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class WeatherQuery(BaseModel):
    city: str = Field(description="城市名称，如'杭州'")
    unit: str = Field(default="c", description="温度单位，c为摄氏度，f为华氏度")


@tool(args_schema=WeatherQuery)
def get_weather_advanced(city: str, unit: str = "c") -> str:
    """获取指定城市的天气，可指定温度单位"""
    # 根据 unit 构建不同请求
    unit_param = "" if unit == "c" else "&u"
    try:
        url = f"https://wttr.in/{city}?format=%C+%t{unit_param}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return f"{city}天气: {response.text.strip()}"
        return f"无法获取{city}的天气"
    except Exception as e:
        return f"查询失败: {e}"


# 把工具放进列表
# tools = [get_weather, get_current_time]
tools = [get_weather_advanced, get_current_time]

llm = ChatOpenAI(
    model="deepseek-v4-pro",
    api_key=os.getenv("DS_API_KEY"),
    base_url=os.getenv("DS_BASE_URL"),
    temperature=0,
)

# 将工具绑定到模型上
llm_with_tools = llm.bind_tools(tools)


# 状态定义：包含消息历史
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# 节点1：调用 LLM
def call_model(state: AgentState) -> AgentState:
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


# 节点2：执行工具调用
def call_tools(state: AgentState) -> AgentState:
    messages = state["messages"]
    last_message = messages[-1]

    tool_result = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        print(f"LangGraph 调用工具：{tool_name}({tool_args})")

        select_tool = next(t for t in tools if t.name == tool_name)
        result = select_tool.invoke(tool_args)
        print(f"工具返回：{result}")

        tool_result.append(
            ToolMessage(
                content=result,
                tool_call_id=tool_call['id']
            )
        )

    return {"messages": tool_result}


# 条件函数：判断是否有工具调用
def should_continue(state: AgentState) -> Literal["tools", "end"]:
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "end"


workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("llm", call_model)
workflow.add_node("tools", call_tools)

# 设置入口点
workflow.set_entry_point("llm")

# 添加条件边：从 llm 出发，根据 should_continue 走向 tools 或结束
workflow.add_conditional_edges(
    "llm",
    should_continue,
    {
        "tools": "tools",
        "end": END
    }
)

# 从 tools 执行完后，回到 llm 继续思考
workflow.add_edge("tools", "llm")

# 编译
app = workflow.compile()

if __name__ == "__main__":
    print("=" * 50)
    print("LangGraph Agent 已启动！输入 'quit' 退出。")
    print("=" * 50)

    while True:
        user_input = input("\n你: ").strip()
        if not user_input:
            continue
        if user_input.lower() == 'quit':
            print("再见！")
            break

        # 初始状态：只包含用户消息
        initial_state = {
            "messages": [
                SystemMessage(content="你是一个智能助手，可以使用工具回答问题。"),
                HumanMessage(content=user_input)
            ]
        }

        result = app.invoke(initial_state)
        # 最后一条消息就是最终回答
        final_message = result["messages"][-1]
        print(f"Agent: {final_message.content}")

        # 生成 Mermaid 图代码
        print("\n=== 图结构 ===")
        print(app.get_graph().draw_mermaid())
