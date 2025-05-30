import asyncio
import uvicorn
import logging
import signal
import sys
import os
from mqtt_handler import start_mqtt_client, stop_mqtt_client
from main import init_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("app-runner")

# 全局变量用于控制优雅关闭
shutdown_event = asyncio.Event()
mqtt_client = None


# 处理终止信号
def handle_shutdown_signal(sig, frame):
    signal_name = signal.Signals(sig).name if hasattr(signal, "Signals") else str(sig)
    logger.info(f"收到信号 {signal_name}，准备关闭服务...")
    shutdown_event.set()


# 注册信号处理程序
signal.signal(signal.SIGINT, handle_shutdown_signal)
signal.signal(signal.SIGTERM, handle_shutdown_signal)


async def start_fastapi():
    """启动FastAPI服务器"""
    config = uvicorn.Config(
        "main:app", host="0.0.0.0", port=8003, reload=False, log_level="info"
    )
    server = uvicorn.Server(config)

    # 在uvicorn中设置shutdown_event
    server.should_exit = shutdown_event.is_set

    await server.serve()


async def shutdown_monitor():
    """监控shutdown_event并等待关闭信号"""
    await shutdown_event.wait()
    return True


async def main():
    """主函数：启动所有服务"""
    global mqtt_client

    try:
        logger.info("正在启动智能农场数据服务...")
        # 手动初始化数据库
        logger.info("手动初始化数据库...")
        try:
            init_db()  # 直接调用初始化函数
            logger.info("数据库初始化成功!")
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            # 不退出程序，继续尝试启动其他服务
        # 启动MQTT客户端
        mqtt_client = start_mqtt_client()
        if not mqtt_client:
            logger.error("MQTT客户端启动失败，退出程序")
            return 1

        # 创建任务来运行FastAPI
        fastapi_task = asyncio.create_task(start_fastapi())
        shutdown_task = asyncio.create_task(shutdown_monitor())

        # 等待任一任务完成或收到关闭信号
        done, pending = await asyncio.wait(
            [fastapi_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        logger.info("正在关闭服务...")

        # 取消所有未完成的任务
        for task in pending:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # 关闭MQTT客户端
        stop_mqtt_client(mqtt_client)

        logger.info("所有服务已关闭")
        return 0

    except Exception as e:
        logger.exception(f"运行服务时出错: {str(e)}")

        # 确保MQTT客户端关闭
        if mqtt_client:
            stop_mqtt_client(mqtt_client)

        return 1


if __name__ == "__main__":
    # 运行主异步函数
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
