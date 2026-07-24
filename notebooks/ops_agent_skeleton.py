from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
import random

class OpsState(TypedDict):
    query: str
    logs: str
    metrics: str
    report: str

# 模拟节点
def fetch_logs(state: OpsState):
    print("[节点] 拉取日志...")
    # 模拟：有时成功，有时失败
    if random.random() > 0.3:
        return {"logs": "错误日志: 支付网关超时，订单ID 1001"}
    else:
        return {"logs": "未发现异常日志"}

def fetch_metrics(state: OpsState):
    print("[节点] 拉取监控指标...")
    return {"metrics": "CPU 使用率 45%，内存 60%，支付网关延迟 500ms"}

def generate_report(state: OpsState):
    print("[节点] 生成分析报告...")
    report = f"根据日志「{state['logs']}」和指标「{state['metrics']}」，初步判断: 支付网关延迟偏高，可能存在网络抖动。"
    return {"report": report}

def decide_next(state: OpsState) -> Literal["metrics", "report"]:
    # 如果日志没找到异常，直接跳到写报告
    if "未发现" in state["logs"]:
        print("[决策] 日志无异常，直接生成报告")
        return "report"
    else:
        print("[决策] 日志有异常，继续拉取指标")
        return "metrics"

# 构建图
workflow = StateGraph(OpsState)
workflow.add_node("fetch_logs", fetch_logs)
workflow.add_node("fetch_metrics", fetch_metrics)
workflow.add_node("generate_report", generate_report)

workflow.set_entry_point("fetch_logs")
workflow.add_conditional_edges("fetch_logs", decide_next, {
    "metrics": "fetch_metrics",
    "report": "generate_report"
})
workflow.add_edge("fetch_metrics", "generate_report")
workflow.add_edge("generate_report", END)

app = workflow.compile()

if __name__ == "__main__":
    print("=== 故障排查 Agent 骨架测试 ===")
    result = app.invoke({"query": "订单1001支付失败", "logs": "", "metrics": "", "report": ""})
    print("\n最终报告:", result["report"])