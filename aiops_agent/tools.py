import sqlite3
from datetime import datetime, timedelta

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from aiops_agent.data import DB_PATH


class SearchLogArgs(BaseModel):
    keyword: str = Field(description="搜索关键词，如 'Timeout'、'NullPointerException'")
    minutes: int = Field(description="查询最近多少分钟的日志，默认30", default=30)


class GetOrderArgs(BaseModel):
    order_id: str = Field(description="订单ID，如 'ORD-FAIL-0001'")


class GetMetricsArgs(BaseModel):
    service_name: str = Field(description="服务名称，如 'payment-service'")
    minutes: int = Field(description="查询最近多少分钟的指标", default=30)


# ---- 工具实现 ----
@tool(args_schema=SearchLogArgs)
def search_logs(keyword: str, minutes: int = 30) -> str:
    """
        在应用日志中搜索包含指定关键词的错误日志。
        可以指定查询最近多少分钟的范围，默认30分钟。
        """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            SELECT timestamp, level, service, message, trace_id 
            FROM logs 
            WHERE message LIKE ? AND timestamp >= ? 
            ORDER BY timestamp DESC 
            LIMIT 20
        """, (f"%{keyword}%", since))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return f"未找到包含'{keyword}'的日志记录（近{minutes}分钟内）"

        result = f"找到 {len(rows)} 条相关日志（近{minutes}分钟内）:\n"
        for r in rows:
            result += f"  [{r['timestamp']}] [{r['level']}] {r['service']}: {r['message']} (trace: {r['trace_id']})\n"
        return result.strip()

    except Exception as e:
        return str(e)


@tool(args_schema=GetOrderArgs)
def get_order_info(order_id: str) -> str:
    """
        根据订单ID查询订单详细信息。
        """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return f"未找到订单 {order_id}"

        return (
            f"订单详情:\n"
            f"  订单ID: {row['id']}\n"
            f"  用户ID: {row['user_id']}\n"
            f"  金额: ¥{row['amount']}\n"
            f"  状态: {row['status']}\n"
            f"  支付方式: {row['payment_method']}\n"
            f"  创建时间: {row['created_at']}\n"
            f"  更新时间: {row['updated_at']}"
        )
    except Exception as e:
        return f"查询订单失败: {str(e)}"


@tool(args_schema=GetMetricsArgs)
def get_system_metrics(service_name: str, minutes: int = 30) -> str:
    """
        查询指定服务的系统监控指标（CPU、内存、响应时间、错误率）。
        """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
                SELECT timestamp, cpu_percent, memory_percent, response_time_ms, error_rate 
                FROM metrics 
                WHERE service = ? AND timestamp >= ? 
                ORDER BY timestamp DESC 
                LIMIT 10
            """, (service_name, since))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return f"未找到服务 {service_name} 近{minutes}分钟的监控数据"

        result = f"服务 {service_name} 近{minutes}分钟监控指标:\n"
        for r in rows:
            result += (
                f"  [{r['timestamp']}] CPU:{r['cpu_percent']}%  "
                f"内存:{r['memory_percent']}%  "
                f"响应时间:{r['response_time_ms']}ms  "
                f"错误率:{r['error_rate']}\n"
            )
        return result.strip()
    except Exception as e:
        return f"查询监控指标失败: {str(e)}"


# 工具集合
ops_tools = [search_logs, get_order_info, get_system_metrics]


if __name__ == "__main__":
    # 测试各个工具
    print("=== 测试 search_logs ===")
    print(search_logs.invoke({"keyword": "Timeout", "minutes": 600}))

    print("\n=== 测试 get_order_info ===")
    print(get_order_info.invoke({"order_id": "ORD-FAIL-0001"}))

    print("\n=== 测试 get_system_metrics ===")
    print(get_system_metrics.invoke({"service_name": "payment-service", "minutes": 600}))
