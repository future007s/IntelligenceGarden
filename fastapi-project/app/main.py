from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from celery import Celery
import taos
import time
import logging
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any, Optional
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("farm-api")

app = FastAPI(
    title="智能农场数据API",
    description="接收和查询农场传感器数据的API服务",
    version="1.0.0",
)

# 允许CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TDengine连接配置
TDENGINE_HOST = os.environ.get("TDENGINE_HOST", "localhost")
TDENGINE_USER = os.environ.get("TDENGINE_USER", "root")
TDENGINE_PASS = os.environ.get("TDENGINE_PASS", "taosdata")
TDENGINE_DB = os.environ.get("TDENGINE_DB", "farm_db")

# MySQL连接配置
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASS = os.environ.get("MYSQL_PASS", "password")
MYSQL_DB = os.environ.get("MYSQL_DB", "farm_info")

# SQLAlchemy设置
SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")

# Redis URL格式：redis://[:password@]host[:port][/database]
redis_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"

# 修改Celery配置使用环境变量
celery = Celery("tasks", broker=redis_url)


# 数据模型
class SensorData(BaseModel):
    sensor_id: str = Field(..., description="传感器ID")
    metric_type: str = Field(..., description="测量类型，如temperature、humidity、ph等")
    value: float = Field(..., description="测量值")
    timestamp: Optional[int] = Field(
        None, description="时间戳(毫秒)，不提供则使用服务器时间"
    )


class SensorDataBatch(BaseModel):
    data: List[SensorData] = Field(..., description="批量传感器数据")


class QueryResult(BaseModel):
    result: Any
    count: int
    time_ms: float


class SensorInfo(BaseModel):
    id: str = Field(..., description="传感器ID")
    name: str = Field(..., description="传感器名称")
    location: str = Field(..., description="安装位置")
    type: str = Field(..., description="传感器类型")
    model: str = Field(..., description="型号")
    description: Optional[str] = Field(None, description="描述信息")
    installation_date: Optional[str] = Field(None, description="安装日期")
    status: str = Field("active", description="状态：active, inactive, maintenance")


# 初始化TDengine连接
def get_taos_conn():
    try:
        return taos.connect(
            host=TDENGINE_HOST,
            user=TDENGINE_USER,
            password=TDENGINE_PASS,
            port=6030,  # 显式指定TDengine端口
            config="/etc/taos",  # 指定配置目录
            timezone="Asia/Shanghai",  # 明确时区
        )
    except Exception as e:
        logger.error(f"连接TDengine失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TDengine连接失败: {str(e)}")


# 初始化MySQL连接
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 直接使用pymysql连接MySQL的简便方法
def get_mysql_conn():
    try:
        return pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASS,
            database=MYSQL_DB,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception as e:
        logger.error(f"连接MySQL失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"MySQL连接失败: {str(e)}")


@app.on_event("startup")
def init_db():
    # 初始化TDengine
    conn = get_taos_conn()
    try:
        # 创建数据库
        conn.execute(
            f"CREATE DATABASE IF NOT EXISTS {TDENGINE_DB} KEEP 365 DAYS 30 BLOCKS 6 UPDATE 1"
        )
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
        logger.info("TDengine数据库初始化完成")
    except Exception as e:
        logger.error(f"初始化TDengine出错: {str(e)}")
        raise
    finally:
        conn.close()

    # 初始化MySQL（可选，如果表已存在则无需创建）
    try:
        # 使用SQLAlchemy创建表
        with engine.connect() as connection:
            # 检查并创建sensors表
            connection.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS sensors (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    location VARCHAR(100) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    description TEXT,
                    installation_date DATE,
                    status VARCHAR(20) DEFAULT 'active'
                )
            """
                )
            )

            # 检查并创建locations表
            connection.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS locations (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    area FLOAT,
                    description TEXT
                )
            """
                )
            )

            connection.commit()

        logger.info("MySQL数据库初始化完成")
    except Exception as e:
        logger.error(f"初始化MySQL出错: {str(e)}")
        # 不抛出异常，因为这不应该阻止应用启动


@app.get("/api/avg/{metric_type}")
async def get_avg_metric(metric_type: str, hours: int = 24, sensor_id: str = None):
    """查询最近N小时某类型传感器的平均值"""
    conn = get_taos_conn()
    start_time = time.time()
    try:
        conn.execute(f"USE {TDENGINE_DB}")

        # 构建查询条件
        where_clause = f"metric_type='{metric_type}'"
        if sensor_id:
            where_clause += f" AND sensor_id='{sensor_id}'"

        res = conn.query(
            f"""
            SELECT AVG(value) as avg_value, MIN(value) as min_value, MAX(value) as max_value 
            FROM sensor_data 
            WHERE {where_clause} AND ts > NOW - {hours}h
            """
        )

        results = res.fetch_all()
        if not results or results[0][0] is None:
            return {
                "result": None,
                "count": 0,
                "time_ms": f"{(time.time() - start_time)*1000:.2f}",
            }

        return {
            "result": {
                "avg": results[0][0],
                "min": results[0][1],
                "max": results[0][2],
                "period": f"{hours}小时",
            },
            "count": len(results),
            "time_ms": f"{(time.time() - start_time)*1000:.2f}",
        }
    finally:
        conn.close()


@app.get("/api/latest/{metric_type}")
async def get_latest_metric(metric_type: str, limit: int = 10, sensor_id: str = None):
    """获取最新的N条指定类型的传感器数据"""
    conn = get_taos_conn()
    start_time = time.time()
    try:
        conn.execute(f"USE {TDENGINE_DB}")

        # 构建查询条件
        where_clause = f"metric_type='{metric_type}'"
        if sensor_id:
            where_clause += f" AND sensor_id='{sensor_id}'"

        res = conn.query(
            f"""
            SELECT ts, value, sensor_id
            FROM sensor_data 
            WHERE {where_clause}
            ORDER BY ts DESC
            LIMIT {limit}
            """
        )

        rows = res.fetch_all()
        column_names = res.fields_names

        results = []
        for row in rows:
            result = {}
            for i, col in enumerate(column_names):
                if col == "ts":
                    result[col] = row[i].strftime("%Y-%m-%d %H:%M:%S.%f")
                else:
                    result[col] = row[i]
            results.append(result)

        return {
            "result": results,
            "count": len(results),
            "time_ms": f"{(time.time() - start_time)*1000:.2f}",
        }
    finally:
        conn.close()


@app.get("/api/sensors")
async def get_sensor_list():
    """获取系统中所有的传感器列表，从MySQL获取详细信息"""
    start_time = time.time()

    # 从TDengine获取活跃传感器ID
    tdengine_conn = get_taos_conn()
    try:
        tdengine_conn.execute(f"USE {TDENGINE_DB}")
        res = tdengine_conn.query(
            """
            SELECT DISTINCT sensor_id 
            FROM sensor_data
            """
        )
        active_sensor_ids = [row[0] for row in res.fetch_all()]
    finally:
        tdengine_conn.close()

    # 从MySQL获取传感器详细信息
    mysql_conn = get_mysql_conn()
    try:
        with mysql_conn.cursor() as cursor:
            # 构建IN查询条件
            if active_sensor_ids:
                id_list = "', '".join(active_sensor_ids)
                cursor.execute(
                    f"""
                    SELECT id, name, location, type, model, description, 
                           DATE_FORMAT(installation_date, '%%Y-%%m-%%d') as installation_date, 
                           status
                    FROM sensors 
                    WHERE id IN ('{id_list}')
                    """
                )
                sensors_info = cursor.fetchall()
            else:
                sensors_info = []

            # 如果有活跃传感器但在MySQL中没有记录，则补充基本信息
            result_dict = {item["id"]: item for item in sensors_info}

            for sensor_id in active_sensor_ids:
                if sensor_id not in result_dict:
                    result_dict[sensor_id] = {
                        "id": sensor_id,
                        "name": f"未命名传感器 {sensor_id}",
                        "location": "未指定",
                        "type": "未知",
                        "model": "未知",
                        "status": "active",
                    }

            # 转换为列表
            final_results = list(result_dict.values())

        return {
            "result": final_results,
            "count": len(final_results),
            "time_ms": f"{(time.time() - start_time)*1000:.2f}",
        }
    finally:
        mysql_conn.close()


@app.get("/api/metrics")
async def get_metrics_list():
    """获取系统中所有的指标类型列表"""
    conn = get_taos_conn()
    start_time = time.time()
    try:
        conn.execute(f"USE {TDENGINE_DB}")
        res = conn.query(
            """
            SELECT DISTINCT metric_type 
            FROM sensor_data
            """
        )
        metrics = [row[0] for row in res.fetch_all()]
        return {
            "result": metrics,
            "count": len(metrics),
            "time_ms": f"{(time.time() - start_time)*1000:.2f}",
        }
    finally:
        conn.close()


# 新增 MySQL 相关API
@app.get("/api/sensor/{sensor_id}")
async def get_sensor_info(sensor_id: str):
    """获取指定传感器的详细信息"""
    start_time = time.time()
    mysql_conn = get_mysql_conn()

    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, location, type, model, description, 
                       DATE_FORMAT(installation_date, '%Y-%m-%d') as installation_date, 
                       status
                FROM sensors 
                WHERE id = %s
                """,
                (sensor_id,),
            )
            result = cursor.fetchone()

        # 获取最新的传感器数据（如果有）
        if result:
            tdengine_conn = get_taos_conn()
            try:
                tdengine_conn.execute(f"USE {TDENGINE_DB}")
                latest_data_res = tdengine_conn.query(
                    f"""
                    SELECT ts, metric_type, value
                    FROM sensor_data
                    WHERE sensor_id = '{sensor_id}'
                    ORDER BY ts DESC
                    LIMIT 10
                    """
                )

                rows = latest_data_res.fetch_all()
                fields = latest_data_res.fields_names

                latest_data = []
                for row in rows:
                    data_point = {}
                    for i, field in enumerate(fields):
                        if field == "ts":
                            data_point[field] = row[i].strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            data_point[field] = row[i]
                    latest_data.append(data_point)

                # 添加到结果中
                result["latest_data"] = latest_data

            except Exception as e:
                logger.warning(f"获取传感器{sensor_id}最新数据失败: {str(e)}")
                result["latest_data"] = []
            finally:
                tdengine_conn.close()

            return {
                "result": result,
                "time_ms": f"{(time.time() - start_time)*1000:.2f}",
            }
        else:
            raise HTTPException(status_code=404, detail=f"传感器 {sensor_id} 不存在")
    finally:
        mysql_conn.close()


@app.post("/api/sensor")
async def create_or_update_sensor(sensor: SensorInfo):
    """创建或更新传感器信息"""
    start_time = time.time()
    mysql_conn = get_mysql_conn()

    try:
        with mysql_conn.cursor() as cursor:
            # 检查传感器是否已存在
            cursor.execute("SELECT id FROM sensors WHERE id = %s", (sensor.id,))
            exists = cursor.fetchone()

            if exists:
                # 更新现有传感器
                cursor.execute(
                    """
                    UPDATE sensors 
                    SET name = %s, location = %s, type = %s, model = %s, 
                        description = %s, installation_date = %s, status = %s
                    WHERE id = %s
                    """,
                    (
                        sensor.name,
                        sensor.location,
                        sensor.type,
                        sensor.model,
                        sensor.description,
                        sensor.installation_date,
                        sensor.status,
                        sensor.id,
                    ),
                )
                message = "传感器信息已更新"
            else:
                # 创建新传感器
                cursor.execute(
                    """
                    INSERT INTO sensors 
                    (id, name, location, type, model, description, installation_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        sensor.id,
                        sensor.name,
                        sensor.location,
                        sensor.type,
                        sensor.model,
                        sensor.description,
                        sensor.installation_date,
                        sensor.status,
                    ),
                )
                message = "传感器信息已创建"

            mysql_conn.commit()

        return {
            "status": "success",
            "message": message,
            "sensor_id": sensor.id,
            "time_ms": f"{(time.time() - start_time)*1000:.2f}ms",
        }
    except Exception as e:
        mysql_conn.rollback()
        logger.error(f"保存传感器信息出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    finally:
        mysql_conn.close()


@app.get("/api/locations")
async def get_locations():
    """获取所有位置信息"""
    start_time = time.time()
    mysql_conn = get_mysql_conn()

    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, type, area, description
                FROM locations
                ORDER BY name
                """
            )
            locations = cursor.fetchall()

        return {
            "result": locations,
            "count": len(locations),
            "time_ms": f"{(time.time() - start_time)*1000:.2f}",
        }
    finally:
        mysql_conn.close()


@app.get("/")
async def root():
    """API服务根路径，返回系统状态"""
    return {
        "status": "online",
        "service": "Farm Sensor Data API",
        "version": "1.0.0",
    }
