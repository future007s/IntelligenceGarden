from celery import Celery
import taos

celery = Celery("tasks", broker="redis://localhost:6379/0")


@celery.task
def analyze_data(data):
    """异步分析任务示例：检测异常值并告警"""
    conn = taos.connect(host="localhost", user="root", password="taosdata")
    try:
        # 示例：检查PH值是否超出安全范围
        if data["metric_type"] == "ph" and (data["value"] < 5 or data["value"] > 8):
            send_alert(f"PH值异常: {data['value']} (设备: {data['sensor_id']})")

        # 可扩展其他分析逻辑（如氮磷钾比例计算）
    finally:
        conn.close()


def send_alert(message: str):
    """模拟发送告警（可集成短信/邮件）"""
    print(f"[ALERT] {message}")