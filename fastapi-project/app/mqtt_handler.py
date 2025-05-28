import paho.mqtt.client as mqtt
import json
import logging
import time
import taos

# 引入配置常量
from main import TDENGINE_HOST, TDENGINE_USER, TDENGINE_PASS, TDENGINE_DB, celery

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mqtt-handler")

# MQTT服务器配置
MQTT_BROKER = "mosquitto"  # Docker网络中的mosquitto服务名称
MQTT_PORT = 1883
MQTT_TOPIC = "farm/sensors/#"  # 订阅所有传感器数据的主题
MQTT_CLIENT_ID = f"farm-server-{int(time.time())}"  # 唯一的客户端ID
MQTT_QOS = 1  # QoS等级1，确保消息至少被传递一次


# 初始化TDengine连接
def get_taos_conn():
    return taos.connect(
        host=TDENGINE_HOST,
        user=TDENGINE_USER,
        password=TDENGINE_PASS,
        database=TDENGINE_DB,
    )


# 处理收到的MQTT消息
def on_message(client, userdata, msg):
    try:
        start_time = time.time()

        # 获取主题和负载
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        logger.info(f"收到MQTT消息 [{topic}]: {payload}")

        # 解析数据为JSON
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.error(f"无效的JSON数据: {payload}")
            return

        # 从主题提取传感器ID (可选)
        # 例如，如果主题是 farm/sensors/dtu001
        topic_parts = topic.split("/")
        if len(topic_parts) >= 3:
            # 使用主题中的传感器ID覆盖或作为默认值
            mqtt_sensor_id = topic_parts[2]
            # 如果data中没有sensor_id，使用主题中的
            if "sensor_id" not in data:
                data["sensor_id"] = mqtt_sensor_id

        # 验证和提取数据字段
        sensor_id = data.get("sensor_id")
        metric_type = data.get("metric_type")
        value = data.get("value")
        timestamp = data.get("timestamp")

        # 验证必要字段
        if not all([sensor_id, metric_type, value is not None]):
            logger.warning(f"消息缺少必要字段: {data}")
            return

        # 确保value是数值
        try:
            value = float(value)
        except (ValueError, TypeError):
            logger.error(f"无效的数值: {value}")
            return

        # 保存到TDengine
        conn = get_taos_conn()
        try:
            # 使用传入的时间戳或当前时间
            ts_value = f"{timestamp}" if timestamp else "NOW"

            # 插入数据到TDengine
            sql = f"""
                INSERT INTO {sensor_id}_{metric_type} 
                USING sensor_data TAGS ('{sensor_id}', '{metric_type}') 
                VALUES ({ts_value}, {value})
            """
            conn.execute(sql)

            # 处理时间统计
            processing_time = (time.time() - start_time) * 1000
            logger.info(
                f"数据已存储: {sensor_id}.{metric_type}={value}, 耗时: {processing_time:.2f}ms"
            )

            # 触发异步分析任务
            celery.send_task(
                "analyze_data",
                args=[
                    {
                        "sensor_id": sensor_id,
                        "metric_type": metric_type,
                        "value": value,
                        "timestamp": timestamp,
                    }
                ],
            )

        except Exception as e:
            logger.exception(f"保存数据到TDengine失败: {str(e)}")
        finally:
            conn.close()

    except Exception as e:
        logger.exception(f"处理MQTT消息时出错: {str(e)}")


# MQTT连接回调
def on_connect(client, userdata, flags, rc):
    connection_result = {
        0: "连接成功",
        1: "协议版本错误",
        2: "无效的客户端标识",
        3: "服务器不可用",
        4: "用户名或密码错误",
        5: "未授权",
    }
    result = connection_result.get(rc, f"未知错误 ({rc})")

    if rc == 0:
        logger.info(f"已连接到MQTT服务器: {result}")
        # 订阅主题
        client.subscribe(MQTT_TOPIC, qos=MQTT_QOS)
        logger.info(f"已订阅主题: {MQTT_TOPIC}")
    else:
        logger.error(f"连接MQTT服务器失败: {result}")


# MQTT断开连接回调
def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("意外断开与MQTT服务器的连接，尝试重新连接...")
    else:
        logger.info("已断开与MQTT服务器的连接")


# 创建和配置MQTT客户端
def create_mqtt_client():
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)

    # 设置回调函数
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # 设置自动重连
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    return client


# 启动MQTT客户端
def start_mqtt_client():
    try:
        logger.info(f"正在连接到MQTT服务器 {MQTT_BROKER}:{MQTT_PORT}...")
        client = create_mqtt_client()

        # 连接到MQTT服务器
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

        # 启动MQTT循环(非阻塞)
        client.loop_start()

        return client
    except Exception as e:
        logger.exception(f"启动MQTT客户端失败: {str(e)}")
        return None


# 停止MQTT客户端
def stop_mqtt_client(client):
    if client:
        logger.info("正在关闭MQTT客户端...")
        client.loop_stop()
        client.disconnect()
        logger.info("MQTT客户端已关闭")


# 当作为独立脚本运行时的入口点
if __name__ == "__main__":
    client = start_mqtt_client()

    try:
        # 保持程序运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_mqtt_client(client)
