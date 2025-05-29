#!/bin/bash

echo "正在应用环境变量配置..."
# 替换配置文件中的环境变量
sed -i "s/localhost/${TDENGINE_HOST:-localhost}/g" main.py
sed -i "s/\"redis:\/\/localhost:6379\/0\"/\"redis:\/\/${REDIS_HOST:-localhost}:${REDIS_PORT:-6379}\/0\"/g" main.py
sed -i "s/MQTT_BROKER = \"mosquitto\"/MQTT_BROKER = \"${MQTT_HOST:-mosquitto}\"/g" mqtt_handler.py
sed -i "s/MQTT_PORT = 1883/MQTT_PORT = ${MQTT_PORT:-1883}/g" mqtt_handler.py

# 添加MySQL环境变量替换
sed -i "s/MYSQL_HOST = \"localhost\"/MYSQL_HOST = \"${MYSQL_HOST:-localhost}\"/g" main.py
sed -i "s/MYSQL_PORT = 3306/MYSQL_PORT = ${MYSQL_PORT:-3306}/g" main.py
sed -i "s/MYSQL_USER = \"root\"/MYSQL_USER = \"${MYSQL_USER:-root}\"/g" main.py
sed -i "s/MYSQL_PASS = \"password\"/MYSQL_PASS = \"${MYSQL_PASS:-farmpassword}\"/g" main.py
sed -i "s/MYSQL_DB = \"farm_info\"/MYSQL_DB = \"${MYSQL_DB:-farm_info}\"/g" main.py

# 同样修改tasks.py中的MySQL配置
if [ -f "tasks.py" ]; then
    sed -i "s/MYSQL_HOST = \"localhost\"/MYSQL_HOST = \"${MYSQL_HOST:-localhost}\"/g" tasks.py
    sed -i "s/MYSQL_PORT = 3306/MYSQL_PORT = ${MYSQL_PORT:-3306}/g" tasks.py
    sed -i "s/MYSQL_USER = \"root\"/MYSQL_USER = \"${MYSQL_USER:-root}\"/g" tasks.py
    sed -i "s/MYSQL_PASS = \"password\"/MYSQL_PASS = \"${MYSQL_PASS:-farmpassword}\"/g" tasks.py
    sed -i "s/MYSQL_DB = \"farm_info\"/MYSQL_DB = \"${MYSQL_DB:-farm_info}\"/g" tasks.py
fi

# MQTT环境变量
sed -i "s/MQTT_BROKER = \"mosquitto\"/MQTT_BROKER = \"${MQTT_HOST:-mosquitto}\"/g" mqtt_handler.py
sed -i "s/MQTT_PORT = 1883/MQTT_PORT = ${MQTT_PORT:-1883}/g" mqtt_handler.py
sed -i "s/MQTT_USERNAME = \"farm_user\"/MQTT_USERNAME = \"${MQTT_USERNAME:-farm_user}\"/g" mqtt_handler.py
sed -i "s/MQTT_PASSWORD = \"secure_password\"/MQTT_PASSWORD = \"${MQTT_PASSWORD:-secure_password}\"/g" mqtt_handler.py

echo "环境变量配置完成"

echo "正在启动 Celery worker..."
# 在后台启动 Celery worker
celery -A tasks worker --loglevel=info &

echo "正在启动 FastAPI 应用和 MQTT 客户端..."
# 启动FastAPI应用和MQTT客户端
exec python run.py
