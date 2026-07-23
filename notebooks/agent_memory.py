import os

import requests
from datetime import datetime
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# 初始化本地 Embedding 模型
embeddings = HuggingFaceEmbeddings(
    model_name="shibing624/text2vec-base-chinese",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

# 长期记忆存储路径
MEMORY_DIR = "./long_term_memory"


class LongTermMemory:
    def __init__(self):
        self.vectordb = Chroma(
            persist_directory=MEMORY_DIR,
            embedding_function=embeddings
        )

    def remember(self, info: str):
        """将一条信息存入长期记忆"""
        self.vectordb.add_texts([info])
        # Chroma 会自动持久化，也可以显式调用 persist
        print(f"[长期记忆] 已记住: {info}")

    def recall(self, query: str, k: int = 3) -> list[str]:
        """根据查询检索最相关的记忆"""
        docs = self.vectordb.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]


load_dotenv()


# ---------- 定义工具 ----------
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


def run_agent(messages: list, user_input: str):
    # ------ 长期记忆召回 ------
    memory = LongTermMemory()
    recall = memory.recall(user_input, k=3)
    if recall:
        memory_context = "\n".join([f'- {m}' for m in recall])
        # 在系统消息中注入记忆
        system_message = SystemMessage(
            content=f"你是一个智能助手。以下是你已知的用户偏好和背景信息：\n{memory_context}\n请据此个性化地回答。"
        )
        # 把原本的系统消息替换掉（或者追加）
        if messages and isinstance(messages[0], SystemMessage):
            messages[0] = system_message
        else:
            messages.insert(0, system_message)

    # ------ 原有 Agent 循环 ------
    max_iterations = 10  # 防止死循环
    for i in range(max_iterations):
        # 调用模型
        response = llm_with_tools.invoke(messages)
        messages.append(response)  # 把模型的回复加入历史

        # 如果模型直接返回了文本答案（没有工具调用），就结束
        if response.content and not response.tool_calls:
            return response.content

        # 如果有工具调用请求，处理每一个工具调用
        if response.tool_calls:
            for tool_call in response.tool_calls:
                # 根据名称找到对应的工具函数
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                print(f"[Agent 决定调用工具] {tool_name}({tool_args})")

                # 执行工具
                selected_tool = next(tool for tool in tools if tool.name == tool_name)
                tool_result = selected_tool.invoke(tool_args)

                print(f"[工具返回] {tool_result}")

                # 把工具执行结果包装成 ToolMessage 追加到对话历史
                messages.append(ToolMessage(content=tool_result, tool_call_id=tool_call["id"]))

        # 如果模型既没输出文本也没调用工具，强制退出（安全保护）
        else:
            break


if __name__ == "__main__":
    print("=" * 50)
    print("AI Agent 已启动！")
    print("输入 'quit' 退出")
    print("输入 '记住：xxx' 存储长期记忆")
    print("=" * 50)

    # 初始化对话历史，系统消息只放一次
    messages = [
        SystemMessage(content="""你是一个乐于助人的智能助手。只有在用户明确询问天气或时间时，才调用相应的工具。
如果用户的问题不需要工具（如介绍城市、闲聊等），请直接回答，不要调用工具。""")
    ]

    while True:
        user_input = input("\n你: ").strip()
        if not user_input:
            continue
        if user_input.lower() == 'quit':
            print("再见！")
            break

        # 处理偏好存储的触发（这里采用手动命令）
        if user_input.startswith("记住："):
            memory = LongTermMemory()
            memory.remember(user_input[3:])
            print("Agent: 好的，我已经记住了。")
            continue

        # 把用户消息加入历史
        messages.append(HumanMessage(content=user_input))

        # 传入完整历史，让 Agent 推理
        final_answer = run_agent(messages, user_input)  # 注意：现在直接传入 messages 列表
        print(f"Agent: {final_answer}")
