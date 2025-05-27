from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery import Celery
import taos  # TDengine客户端

app = FastAPI()

# TDengine连接配置
TDENGINE_HOST = "localhost"
TDENGINE_USER = "root"
TDENGINE_PASS = "taosdata"
TDENGINE_DB = "farm_db"

# Celery配置
celery = Celery("tasks", broker="redis://localhost:6379/0")


# 数据模型
class SensorData(BaseModel):
    sensor_id: str
    metric_type: str  # e.g. "temperature", "ph"
    value: float
    timestamp: int = None  # 可选，默认用服务器时间


# 初始化TDengine连接
def get_taos_conn():
    return taos.connect(host=TDENGINE_HOST, user=TDENGINE_USER, password=TDENGINE_PASS)


@app.on_event("startup")
def init_db():
    conn = get_taos_conn()
    conn.execute(f"CREATE DATABASE IF NOT EXISTS {TDENGINE_DB}")
    conn.execute(f"USE {TDENGINE_DB}")
    # 创建超级表（模板）
    conn.execute(
        """
        CREATE STABLE IF NOT EXISTS sensor_data (
            ts TIMESTAMP,
            value FLOAT
        ) TAGS (
            sensor_id BINARY(50),
            metric_type BINARY(20)
        )
    """
    )
    conn.close()


@app.post("/api/sensor-data")
async def receive_data(data: SensorData):
    """接收传感器数据并写入TDengine"""
    try:
        conn = get_taos_conn()
        conn.execute(f"USE {TDENGINE_DB}")
        # 插入数据到子表（自动创建）
        sql = f"""
            INSERT INTO {data.sensor_id}_{data.metric_type} 
            USING sensor_data TAGS ('{data.sensor_id}', '{data.metric_type}') 
            VALUES (NOW, {data.value})
        """
        conn.execute(sql)

        # 触发异步分析任务
        celery.send_task("analyze_data", args=[data.model_dump()])

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/avg-temperature")
async def get_avg_temp(hours: int = 24):
    """查询最近N小时平均温度（演示分析查询）"""
    conn = get_taos_conn()
    try:
        res = conn.query(
            f"""
            SELECT AVG(value) 
            FROM sensor_data 
            WHERE metric_type='temperature' AND ts > NOW - {hours}h
        """
        )
        return {"avg_temperature": res.fetch_all()[0][0]}
    finally:
        conn.close()