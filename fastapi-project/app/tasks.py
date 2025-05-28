from celery import Celery
import taos
import logging
import time
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("celery-tasks")

# TDengine连接配置
TDENGINE_HOST = "localhost"
TDENGINE_USER = "root"
TDENGINE_PASS = "taosdata"
TDENGINE_DB = "farm_db"

# 创建Celery应用
celery_app = Celery("tasks", broker="redis://localhost:6379/0")

# 配置Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
)


# 初始化TDengine连接
def get_taos_conn():
    return taos.connect(
        host=TDENGINE_HOST,
        user=TDENGINE_USER,
        password=TDENGINE_PASS,
        database=TDENGINE_DB,
    )


@celery_app.task(name="analyze_data")
def analyze_data(data):
    """
    分析传感器数据的异步任务

    参数:
    data - 包含传感器数据的字典
    """
    try:
        start_time = time.time()
        logger.info(f"开始分析数据: {data}")

        sensor_id = data.get("sensor_id")
        metric_type = data.get("metric_type")
        value = data.get("value")

        if not all([sensor_id, metric_type, value is not None]):
            logger.warning(f"数据不完整，跳过分析: {data}")
            return {"status": "skipped", "reason": "incomplete_data"}

        # 连接数据库
        conn = get_taos_conn()

        # 基于不同的指标类型执行不同的分析
        if metric_type == "temperature":
            # 分析温度数据
            if value > 35:
                logger.warning(f"检测到高温告警! 传感器: {sensor_id}, 值: {value}°C")
                # 这里可以添加告警逻辑，如发送通知等

            # 查询该传感器过去1小时的平均温度
            result = conn.query(
                f"""
                SELECT AVG(value) as avg_temp FROM sensor_data 
                WHERE sensor_id='{sensor_id}' AND metric_type='temperature'
                AND ts > NOW - 1h
            """
            )
            rows = result.fetch_all()
            if rows and rows[0][0] is not None:
                avg_temp = rows[0][0]
                logger.info(f"传感器 {sensor_id} 过去1小时平均温度: {avg_temp:.2f}°C")

                # 检测温度变化趋势
                if value > avg_temp * 1.2:
                    logger.warning(
                        f"传感器 {sensor_id} 温度上升显著，当前: {value}°C, 平均: {avg_temp:.2f}°C"
                    )

        elif metric_type == "humidity":
            # 分析湿度数据
            if value > 90:
                logger.warning(f"检测到高湿度告警! 传感器: {sensor_id}, 值: {value}%")
            elif value < 20:
                logger.warning(f"检测到低湿度告警! 传感器: {sensor_id}, 值: {value}%")

        elif metric_type == "ph":
            # 分析pH值
            if value < 5.5 or value > 7.5:
                logger.warning(f"pH值超出正常范围! 传感器: {sensor_id}, 值: {value}")

        # 可以添加更多指标类型的分析...

        conn.close()
        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"数据分析完成: {sensor_id}.{metric_type}, 耗时: {processing_time:.2f}ms"
        )
        return {
            "status": "success",
            "analyzed": data,
            "processing_time_ms": processing_time,
        }

    except Exception as e:
        logger.exception(f"数据分析出错: {str(e)}")
        return {"status": "error", "message": str(e)}


# 添加更多Celery任务...
@celery_app.task(name="daily_report")
def generate_daily_report():
    """生成每日报告的任务，可以通过Celery Beat定时调度"""
    try:
        logger.info("开始生成每日报告...")

        conn = get_taos_conn()

        # 查询昨天的温度统计
        temp_result = conn.query(
            """
            SELECT 
                AVG(value) as avg_temp,
                MAX(value) as max_temp,
                MIN(value) as min_temp
            FROM sensor_data 
            WHERE metric_type='temperature'
            AND ts >= CURDATE() - 1d
            AND ts < CURDATE()
        """
        )

        rows = temp_result.fetch_all()
        if rows and rows[0][0] is not None:
            avg_temp = rows[0][0]
            max_temp = rows[0][1]
            min_temp = rows[0][2]

            logger.info(
                f"昨日温度统计: 平均={avg_temp:.2f}°C, 最高={max_temp:.2f}°C, 最低={min_temp:.2f}°C"
            )

        # 可以添加更多统计逻辑...

        conn.close()
        return {"status": "success", "report_date": datetime.now().strftime("%Y-%m-%d")}

    except Exception as e:
        logger.exception(f"生成每日报告出错: {str(e)}")
        return {"status": "error", "message": str(e)}
