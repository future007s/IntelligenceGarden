-- 创建数据库(如果不存在)
CREATE DATABASE IF NOT EXISTS farm_info CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE farm_info;

-- 传感器表
CREATE TABLE IF NOT EXISTS sensors (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    description TEXT,
    installation_date DATE,
    status VARCHAR(20) DEFAULT 'active'
);

-- 位置表
CREATE TABLE IF NOT EXISTS locations (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    area FLOAT,
    description TEXT
);

-- 传感器阈值配置表
CREATE TABLE IF NOT EXISTS sensor_thresholds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sensor_id VARCHAR(50) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    min_value FLOAT,
    max_value FLOAT,
    warning_min FLOAT,
    warning_max FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (sensor_id) REFERENCES sensors(id) ON DELETE CASCADE,
    UNIQUE KEY (sensor_id, metric_type)
);

-- 告警记录表
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sensor_id VARCHAR(50) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    value FLOAT NOT NULL,
    threshold_value FLOAT,
    alert_type ENUM('high', 'low', 'offline', 'other') NOT NULL,
    severity ENUM('info', 'warning', 'critical') NOT NULL,
    status ENUM('active', 'acknowledged', 'resolved') DEFAULT 'active',
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    FOREIGN KEY (sensor_id) REFERENCES sensors(id)
);

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE,
    role ENUM('admin', 'user', 'viewer') NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

-- 插入一些测试数据
INSERT INTO locations (id, name, type, area, description)
VALUES 
('greenhouse1', '1号温室', 'greenhouse', 500.0, '蔬菜种植温室'),
('greenhouse2', '2号温室', 'greenhouse', 450.0, '花卉种植温室'),
('field1', '东区大田', 'field', 2000.0, '水稻种植区'),
('field2', '西区大田', 'field', 1800.0, '玉米种植区');

INSERT INTO sensors (id, name, location, type, model, installation_date, description, status)
VALUES 
('temp001', '温度传感器01', 'greenhouse1', 'temperature', 'DHT22', '2023-01-15', '1号温室主温度传感器', 'active'),
('hum001', '湿度传感器01', 'greenhouse1', 'humidity', 'DHT22', '2023-01-15', '1号温室主湿度传感器', 'active'),
('soil001', '土壤湿度01', 'field1', 'soil_moisture', 'SM100', '2023-03-20', '东区土壤湿度监测', 'active'),
('light001', '光照强度01', 'greenhouse2', 'light', 'BH1750', '2023-02-10', '2号温室光照监测', 'active');

-- 添加示例阈值配置
INSERT INTO sensor_thresholds (sensor_id, metric_type, min_value, max_value, warning_min, warning_max)
VALUES
('temp001', 'temperature', 10.0, 40.0, 15.0, 35.0),
('hum001', 'humidity', 20.0, 90.0, 30.0, 80.0),
('soil001', 'soil_moisture', 15.0, 75.0, 20.0, 70.0);

-- 添加默认管理员用户 (密码为 admin123)
-- 注意：实际部署时应使用正确的密码哈希
INSERT INTO users (username, password_hash, email, role)
VALUES ('admin', '$2b$12$ILId.oc9YYAHYrQQRVJwOej2bAFQdzQFuZkJ7b2UbVrvxDpgkAA36', 'admin@example.com', 'admin');