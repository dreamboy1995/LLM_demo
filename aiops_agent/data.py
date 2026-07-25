import random
import sqlite3
from datetime import datetime, timedelta

from faker import Faker

fake = Faker("zh_CN")  # 中文数据
DB_PATH = "aiops_data.db"


def init_db():
    """创建数据库表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 订单表
    cursor.execute(
        """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                amount REAL,
                status TEXT,
                payment_method TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """
    )

    # 应用日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            service TEXT,
            message TEXT,
            trace_id TEXT
        )
    """)

    # 系统监控指标表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            service TEXT,
            cpu_percent REAL,
            memory_percent REAL,
            response_time_ms REAL,
            error_rate REAL
        )
    """)

    conn.commit()
    conn.close()
    print("数据库表创建成功")


def generate_orders(num=50):
    """生成模拟订单数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    statuses = ["paid", "pending", "failed", "refunded"]
    payment_methods = ["alipay", "wechat", "credit_card"]

    for _ in range(num):
        order_id = f"ORD-{fake.unique.random_number(digits=6)}"
        user_id = f"USR-{random.randint(1000, 9999)}"
        amount = round(random.uniform(10, 500), 2)
        status = random.choice(statuses)
        payment_method = random.choice(payment_methods)
        created_at = fake.date_time_between(
            start_date="-7d", end_date="now"
        ).strftime("%Y-%m-%d %H:%M:%S")
        updated_at = (datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S") +
                      timedelta(minutes=random.randint(1, 60))).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT OR IGNORE INTO orders 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (order_id, user_id, amount, status, payment_method, created_at, updated_at))

    conn.commit()
    conn.close()
    print(f"已生成 {num} 条订单数据")


def generate_logs(num=200):
    """生成模拟日志，插入一些典型故障日志"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    services = ["order-service", "payment-service", "user-service", "gateway"]
    levels = ["INFO", "WARN", "ERROR"]
    normal_messages = [
        "Request processed successfully",
        "Connection pool refreshed",
        "Cache hit for key user:{}",
        "Scheduled task completed"
    ]
    error_messages = [
        "Timeout while calling payment gateway",
        "Connection refused to database",
        "NullPointerException in OrderService.process",
        "OutOfMemoryError: Java heap space",
        "Circuit breaker opened for service payment",
        "Slow query detected: 5.2 seconds"
    ]

    for _ in range(num):
        timestamp = fake.date_time_between(
            start_date="-1d", end_date="now"
        ).strftime("%Y-%m-%d %H:%M:%S")
        service = random.choice(services)
        # 故意提高 ERROR 比例，产生可排查的故障
        level = random.choices(
            ["INFO", "WARN", "ERROR"], weights=[50, 30, 20]
        )[0]
        trace_id = fake.uuid4()

        if level == "ERROR":
            message = random.choice(error_messages)
        else:
            message = random.choice(normal_messages)

        cursor.execute("""
            INSERT INTO logs (timestamp, level, service, message, trace_id)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, level, service, message, trace_id))

    conn.commit()
    conn.close()
    print(f"已生成 {num} 条日志数据")


def generate_metrics(num=100):
    """生成模拟监控指标，制造一些异常点"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    services = ["order-service", "payment-service", "user-service"]

    for _ in range(num):
        timestamp = fake.date_time_between(
            start_date="-6h", end_date="now"
        ).strftime("%Y-%m-%d %H:%M:%S")
        service = random.choice(services)

        # 正常情况下 CPU 30%~60%，但偶尔飙高
        cpu = round(random.uniform(30, 60), 1)
        memory = round(random.uniform(40, 70), 1)
        response_time = round(random.uniform(20, 200), 1)
        error_rate = 0.0

        # 制造一个明显的异常点：payment-service 在某段时间响应时间飙升
        if service == "payment-service" and random.random() < 0.3:
            response_time = round(random.uniform(500, 2000), 1)
            error_rate = round(random.uniform(0.05, 0.3), 2)

        cursor.execute("""
            INSERT INTO metrics (timestamp, service, cpu_percent, memory_percent, response_time_ms, error_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, service, cpu, memory, response_time, error_rate))

    conn.commit()
    conn.close()
    print(f"已生成 {num} 条监控数据")


if __name__ == "__main__":
    init_db()
    generate_orders(50)
    generate_logs(200)
    generate_metrics(100)
    print("\n全部模拟数据生成完毕！")