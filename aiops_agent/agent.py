import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Literal
from langgraph.graph import add_messages, StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, HumanMessage

# 加载环境变量
load_dotenv()

# 我们定义好的三个工具
from aiops_agent.tools import ops_tools

# 初始化 LLM（用 DeepSeek，也支持通义千问）
llm = ChatOpenAI(
    model="deepseek-v4-pro",
    api_key=os.getenv("DS_API_KEY"),
    base_url=os.getenv("DS_BASE_URL"),
    temperature=0  # 排查故障需要严谨，随机性设为0
)

# 将工具绑定到模型
llm_with_tools = llm.bind_tools(ops_tools)


# 状态定义
class AgentState(TypedDict):  # TypedDict定义一个带有类型约束的字典结构
    messages: Annotated[list[BaseMessage], add_messages]  # Annotated为类型添加元数据注解


# LLM 节点
def call_model(state: AgentState) -> AgentState:
    """调用 LLM，分析当前信息并决定下一步动作"""
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 工具执行节点
def call_tools(state: AgentState)->AgentState:
    """执行 LLM 请求的工具调用，并将结果包装成 ToolMessage"""
    messages = state["messages"]
    last_message = messages[-1]

    tool_results = []
    for tool in last_message.tool_calls:
        tool_name = tool["name"]
        tool_args = tool["args"]
        print(f"[Agent 调用工具] {tool_name}({tool_args})")

        # 从工具列表中匹配
        selected_tool = next((tool for tool in ops_tools if tool.name == tool_name), None)
        result = selected_tool.invoke(tool_args)
        print(f"[工具返回] {result[:100]}...")  # 只打印前100字符，避免刷屏

        tool_results.append(ToolMessage(
            tool_call_id=tool["id"],
            content=result
        ))

    return {"messages": tool_results}

# 条件边：判断是否继续调用工具
def should_continue(state:AgentState)->Literal["tools", "end"]:
    """检查最后一条消息是否包含工具调用"""
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "end"

# 构建图
def create_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node('llm',call_model)
    workflow.add_node('tools',call_tools)
    workflow.set_entry_point('llm')
    workflow.add_conditional_edges(
        'llm',
        should_continue,
        {'tools': 'tools', 'end': END}
    )
    workflow.add_edge('tools','llm')

    return workflow.compile()


def print_welcome():
    print("=" * 60)
    print("  🔧 AIOps 智能故障排查 Agent")
    print("  支持场景：支付超时、数据库连接、空指针等")
    print("  试试问：'订单 ORD-FAIL-0001 为什么支付失败？'")
    print("  输入 'quit' 退出")
    print("=" * 60)


if __name__ == "__main__":
    load_dotenv()
    app = create_agent_graph()
    print_welcome()

    # 系统提示词，定义 Agent 角色和输出格式
    system_prompt = (
        "你是一个资深的线上故障排查专家（SRE）。"
        "你的任务是利用提供的工具（search_logs, get_order_info, get_system_metrics）"
        "帮助用户分析故障原因，并给出明确的根因分析和解决建议。\n\n"
        "分析步骤建议：\n"
        "1. 如果有订单ID，先用 get_order_info 查看订单详情。\n"
        "2. 用 search_logs 搜索相关错误日志，关键词可以是 'Timeout', 'Exception', 'refused' 等。\n"
        "3. 用 get_system_metrics 查看对应服务的 CPU、内存、响应时间等指标。\n"
        "4. 综合以上信息，给出根因分析，格式如下：\n"
        "   - 故障现象：xxx\n"
        "   - 排查过程：xxx\n"
        "   - 根因：xxx\n"
        "   - 建议：xxx\n\n"
        "注意：如果一次获取的信息不足，可以继续调用工具扩大搜索范围。"
    )

    while True:
        user_input = input("\n👤 你: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ('quit', 'exit', 'q'):
            print("再见！")
            break

        # 构建初始消息
        initial_state = {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]
        }

        print("\n🤖 Agent 正在排查...")
        try:
            result = app.invoke(initial_state)
            final_message = result["messages"][-1]
            print(f"\n📋 分析报告:\n{final_message.content}")
        except Exception as e:
            print(f"\n❌ 排查过程出错: {e}")