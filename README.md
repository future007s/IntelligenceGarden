# IntelligenceGarden - 智能农场数据平台

## 项目概述

智能农场数据平台是一套集成数据采集、存储、分析和可视化的系统，专为农业物联网场景设计。系统采用 MQTT 协议高效接收传感器数据，通过 FastAPI 提供 RESTful 接口，并使用 TDengine 高效存储时序数据，MySQL 管理结构化信息。

## 核心组件

- **MQTT 服务** - 高效低功耗的数据接收通道
- **FastAPI** - 高性能 API 服务
- **TDengine** - 时序数据库，存储传感器数据
- **MySQL** - 关系型数据库，存储设备信息
- **Redis** - 缓存和消息队列
- **Celery** - 异步任务处理
- **Prometheus** - 系统监控

## 目录结构

```
IntelligenceGarden/
├── fastapi-tdengine-project/
│   ├── app/
│   │   ├── main.py           # FastAPI主程序
│   │   ├── mqtt_handler.py   # MQTT客户端处理
│   │   ├── tasks.py          # Celery任务定义
│   │   └── run.py            # 应用启动程序
│   ├── mosquitto/
│   │   └── config/
│   │       └── mosquitto.conf # MQTT服务器配置
│   ├── mysql/
│   │   └── init/
│   │       └── 01-schema.sql  # MySQL初始化脚本
│   ├── docker-compose.yml    # 容器编排配置
│   ├── Dockerfile            # FastAPI服务容器配置
│   ├── requirements.txt      # Python依赖
│   ├── start.sh              # 容器启动脚本
│   └── prometheus.yml        # Prometheus配置
└── README.md                 # 项目文档
```

## 快速开始

### 前置条件

- Docker 和 Docker Compose
- 4G DTU 设备（支持 MQTT 协议）
- 网络连接

### 部署步骤

1. 克隆仓库

```bash
git clone https://github.com/your-username/IntelligenceGarden.git
cd IntelligenceGarden/fastapi-project
```

2. 修改配置文件

```bash
# 编辑docker-compose.yml修改敏感配置
nano docker-compose.yml

# 编辑MySQL初始化脚本
nano mysql/init/01-schema.sql

# 编辑MQTT配置
nano mosquitto/config/mosquitto.conf
```

3. 部署服务

```bash
# 首先构建自定义镜像
docker-compose build

# 然后启动所有服务
docker-compose up -d
```

4. 验证服务

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f fastapi
```

## 配置项说明

### docker-compose.yml 关键配置项

| 服务     | 配置项              | 默认值         | 说明                | 是否需修改 |
| -------- | ------------------- | -------------- | ------------------- | ---------- |
| fastapi  | TDENGINE_HOST       | tdengine       | TDengine 服务器地址 | 否         |
| fastapi  | TDENGINE_USER       | root           | TDengine 用户名     | 否         |
| fastapi  | TDENGINE_PASS       | taosdata       | TDengine 密码       | **是**     |
| fastapi  | TDENGINE_DB         | farm_db        | TDengine 数据库     | 可选       |
| fastapi  | MYSQL_HOST          | mysql          | MySQL 服务器地址    | 否         |
| fastapi  | MYSQL_PORT          | 3306           | MySQL 端口          | 否         |
| fastapi  | MYSQL_USER          | root           | MySQL 用户名        | 否         |
| fastapi  | MYSQL_PASS          | 870803         | MySQL 密码          | **是**     |
| fastapi  | MYSQL_DB            | farm_info      | MySQL 数据库名      | 可选       |
| fastapi  | REDIS_HOST          | redis          | Redis 服务器地址    | 否         |
| fastapi  | MQTT_HOST           | mosquitto      | MQTT 服务器地址     | 否         |
| mysql    | MYSQL_ROOT_PASSWORD | 870803         | MySQL 根密码        | **是**     |
| 所有服务 | restart             | unless-stopped | 重启策略            | 否         |
| 所有服务 | networks            | farm-network   | 网络配置            | 否         |

### 端口映射配置

| 服务       | 端口映射  | 说明                    | 是否需修改 |
| ---------- | --------- | ----------------------- | ---------- |
| fastapi    | 8003:8003 | FastAPI 端口            | 可选       |
| mysql      | 3306:3306 | MySQL 端口              | 可选       |
| tdengine   | 6030:6030 | TDengine 服务端口       | 可选       |
| tdengine   | 6041:6041 | TDengine REST API 端口  | 可选       |
| mosquitto  | 1883:1883 | MQTT 标准端口           | 一般保留   |
| mosquitto  | 9001:9001 | MQTT WebSocket 端口     | 可选       |
| prometheus | 9090:9090 | Prometheus Web 界面端口 | 可选       |
| redis      | 6379:6379 | Redis 端口              | 可选       |

### MQTT 配置 (mosquitto.conf)

```conf
# 基本配置
listener 1883
allow_anonymous true  # 生产环境建议设为false并配置用户认证

# WebSocket支持
listener 9001
protocol websockets

# 持久化配置
persistence true
persistence_location /mosquitto/data/

# 日志配置
log_dest file /mosquitto/log/mosquitto.log
log_type all
```

### MySQL 初始化脚本 (01-schema.sql)

包含项目所需的数据表：

- `sensors` - 传感器信息表
- `locations` - 位置信息表

## API 端点说明

| 端点                        | 方法 | 说明                     |
| --------------------------- | ---- | ------------------------ |
| `/api/avg/{metric_type}`    | GET  | 获取指定指标类型的平均值 |
| `/api/latest/{metric_type}` | GET  | 获取最新的传感器数据     |
| `/api/sensors`              | GET  | 获取所有传感器列表       |
| `/api/sensor/{sensor_id}`   | GET  | 获取单个传感器详情       |
| `/api/sensor`               | POST | 创建或更新传感器信息     |
| `/api/metrics`              | GET  | 获取所有指标类型列表     |
| `/api/locations`            | GET  | 获取所有位置信息         |

## DTU 设备配置指南

对于连接系统的 4G DTU 设备，建议配置如下：

### MQTT 连接参数

- **服务器地址**: 您服务器的 IP 或域名
- **端口**: 1883
- **协议**: MQTT v3.1.1
- **主题格式**: `farm/sensors/{设备ID}`
- **消息格式**:
  ```json
  {
    "sensor_id": "dtu001",
    "metric_type": "temperature",
    "value": 25.6
  }
  ```
- **QoS 级别**: 1 (至少一次送达)
- **保持连接**: 60 秒
- **客户端 ID**: 每个设备唯一
- **自动重连**: 开启

## 监控与维护

### Prometheus 监控

Prometheus 提供了系统级监控能力，包括：

- 服务器资源使用情况
- 容器健康状态
- API 响应时间
- 数据流量统计

访问方式：`http://服务器IP:9090`

建议配合 Grafana 使用，创建可视化仪表盘。

### 日志查看

```bash
# 查看FastAPI日志
docker-compose logs -f fastapi

# 查看MQTT日志
docker-compose logs -f mosquitto

# 查看TDengine日志
docker-compose logs -f tdengine
```

### 数据备份

```bash
# 备份MySQL数据
docker exec -it fastapi-tdengine-project_mysql_1 \
  mysqldump -u root -p870803 farm_info > farm_backup.sql

# 备份TDengine数据
# 需要TDengine支持，具体命令以官方文档为准
```

## 安全建议

1. 修改所有默认密码
2. 为 MQTT 服务器配置用户认证
3. 限制数据库端口只对内部网络开放
4. 实施 API 访问控制和认证
5. 定期更新容器镜像
6. 配置防火墙规则
7. 定期备份数据

## 常见问题

**Q: 如何扩展系统容量？**  
A: 可以通过调整 TDengine 和 MySQL 的存储配置，或实施分布式部署。

**Q: 4G DTU 设备耗电高吗？**  
A: 使用 MQTT 协议的 DTU 设备非常节能，协议开销小，且支持休眠模式。

## 贡献指南

欢迎提交 Issue 和 Pull Request。开发时请遵循以下规范：

1. 遵循 PEP8 代码风格
2. 添加单元测试
3. 使用有意义的提交消息
4. 更新文档

## 许可证

MIT License
