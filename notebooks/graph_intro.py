# 1. 定义状态：在节点之间流转的数据
from typing import TypedDict

from langgraph.graph import StateGraph, END


class GraphState(TypedDict):
    name: str
    greeting: str


# 2. 定义节点函数：接收状态，返回更新后的状态
def start_node(state: GraphState) -> GraphState:
    print(f"[start_node] 收到名字：{state['name']}")
    return {"greeting": f"你好，{state['name']}!"}


def uppercase_node(state: GraphState) -> GraphState:
    greeting = state["greeting"]
    return {"greeting": greeting.upper()}


def goodbye_node(state: GraphState) -> GraphState:
    print(f"[goodbye_node] 最终问候：{state['greeting']}")
    return state


# 3. 创建状态图
workflow = StateGraph(GraphState)

# 4. 添加节点
workflow.add_node('start', start_node)
workflow.add_node('uppercase', uppercase_node)
workflow.add_node('goodbye', goodbye_node)

# 5. 添加边：定义执行顺序
workflow.set_entry_point('start')  # 入口
workflow.add_edge('start', 'uppercase')  # start → uppercase
workflow.add_edge('uppercase', 'goodbye')  # uppercase → goodbye
workflow.add_edge('goodbye', END)  # goodbye → 结束

# 6. 编译并运行
app = workflow.compile()
result = app.invoke({"name": "World", "greeting": ""})
print(f'最终状态：{result}')
