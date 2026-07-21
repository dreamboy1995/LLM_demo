import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

# 加载 .env 文件中的环境变量
load_dotenv()

# 创建模型实例
# DeepSeek 和通义千问都兼容 OpenAI 的 API 格式，所以用 ChatOpenAI 即可
llm = ChatOpenAI(
    model="deepseek-v4-pro",
    api_key=os.getenv("DS_API_KEY"),
    base_url=os.getenv("DS_BASE_URL"),
    temperature=0.1,  # 创造性程度，0=确定性回答，1=更有创造性
    max_tokens=512,  # 生成的最大 token 数
)

# 发送一条消息
response = llm.invoke("请用通俗易懂的语言解释什么是API网关")
print(response.content)

# 多轮对话
messages = [
    SystemMessage(content="你是一个专业的技术面试官，请用简洁的方式回答，不超过100字。"),
    HumanMessage(content="什么是RESTful API？"),
    HumanMessage(content="它和GraphQL有什么区别？"),
]
response = llm.invoke(messages)
print("\n===========多轮对话===========")
print(response.content)
