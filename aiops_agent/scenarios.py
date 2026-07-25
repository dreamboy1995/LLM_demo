# aiops_agent/scenarios.py
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "aiops_data.db"


def inject_scenario_1_payment_timeout():
    """
    场景1：支付网关超时
    现象：大量订单支付失败，日志出现Timeout while calling payment gateway
    根因：支付服务响应时间飙升至2000ms，触发超时
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 插入一批失败的订单
    for i in range(10):
        order_id = f"ORD-FAIL-{i:04d}"
        now = datetime.now()
        cursor.execute("""
            INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, "USR-5001", 99.9, "failed", "alipay",
            (now - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
            now.strftime("%Y-%m-%d %H:%M:%S")
        ))

    # 插入对应错误日志
    for i in range(10):
        now = datetime.now()
        cursor.execute("""
            INSERT INTO logs (timestamp, level, service, message, trace_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            (now - timedelta(minutes=30 + i)).strftime("%Y-%m-%d %H:%M:%S"),
            "ERROR", "payment-service",
            "Timeout while calling payment gateway",
            f"trace-pay-{i}"
        ))

    # 插入监控异常
    for i in range(5):
        t = datetime.now() - timedelta(minutes=30 + i * 5)
        cursor.execute("""
            INSERT INTO metrics (timestamp, service, cpu_percent, memory_percent, response_time_ms, error_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            t.strftime("%Y-%m-%d %H:%M:%S"),
            "payment-service", 55.0, 70.0, 1500 + i * 100, 0.25
        ))

    conn.commit()
    conn.close()
    print("场景1注入完成：支付网关超时")


def inject_scenario_2_db_connection_refused():
    """
    场景2：数据库连接被拒绝
    现象：order-service 大量报错 Connection refused to database
    根因：数据库连接池耗尽
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for i in range(8):
        now = datetime.now()
        cursor.execute("""
            INSERT INTO logs (timestamp, level, service, message, trace_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            (now - timedelta(minutes=10 + i)).strftime("%Y-%m-%d %H:%M:%S"),
            "ERROR", "order-service",
            "Connection refused to database",
            f"trace-db-{i}"
        ))

    conn.commit()
    conn.close()
    print("场景2注入完成：数据库连接被拒绝")


def inject_scenario_3_null_pointer():
    """
    场景3：订单处理空指针异常
    现象：order-service 抛出 NullPointerException
    根因：上游传递了空的产品ID
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for i in range(6):
        now = datetime.now()
        cursor.execute("""
            INSERT INTO logs (timestamp, level, service, message, trace_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            (now - timedelta(minutes=5 * i)).strftime("%Y-%m-%d %H:%M:%S"),
            "ERROR", "order-service",
            "NullPointerException in OrderService.process",
            f"trace-null-{i}"
        ))

    conn.commit()
    conn.close()
    print("场景3注入完成：空指针异常")


if __name__ == "__main__":
    inject_scenario_1_payment_timeout()
    inject_scenario_2_db_connection_refused()
    inject_scenario_3_null_pointer()
    print("全部故障场景注入完毕！")