import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-v4-pro",
    api_key=os.getenv("DS_API_KEY"),
    base_url=os.getenv("DS_BASE_URL"),
    temperature=0.1,  # 创造性程度，0=确定性回答，1=更有创造性
)


def get_weather(city: str) -> str:
    """获取城市天气（模拟版本，避免注册额外API）"""
    # 公开的免费天气API，无需注册
    try:
        # 使用 wttr.in 提供的免费天气接口
        url = f"https://wttr.in/{city}?format=%C+%t+%w"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return f"{city}天气：{response.text.strip()}"
        return f"无法获取{city}的天气信息"
    except Exception as e:
        return f"查询天气失败：{e}"


def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == '__main__':
    print("=" * 50)
    print("聊天机器人已启动！(输入 'quit' 退出, 'time' 查时间, 'weather 城市名' 查天气)")
    print("=" * 50)

    while True:
        user_input = input("\n你：").strip()
        if not user_input:
            continue
        if user_input.lower() == 'quit':
            print('再见！')
            break

        # 处理特殊命令
        if user_input == 'time':
            print(f"机器人：现在是{get_current_time()}")
            continue
        if user_input.startswith('weather '):
            city = user_input[8:].strip()
            print(f"机器人：{get_weather(city)}")
            continue

        # 一般对话，交给LLM
        response = llm.invoke(user_input)
        print(f"机器人：{response.content}")