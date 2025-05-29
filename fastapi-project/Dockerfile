FROM tdengine/tdengine:3.0.5.0 as tdengine
FROM python:3.12.6

# 安装jemalloc依赖
RUN apt-get update && apt-get install -y libjemalloc-dev

# 从TDengine镜像复制客户端库
COPY --from=tdengine /usr/local/taos/ /usr/local/taos/
COPY --from=tdengine /usr/lib/libtaos.* /usr/lib/
RUN ldconfig

# 设置TDengine环境变量
ENV LD_LIBRARY_PATH="/usr/lib:/usr/local/taos/driver:${LD_LIBRARY_PATH}"
ENV TAOS_HOME="/usr/local/taos"
# 添加这行以解决TLS问题
ENV LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libjemalloc.so.2"

# 创建明确的符号链接
RUN cd /usr/lib && ln -sf libtaos.so.* libtaos.so

# 检查库文件是否存在并可访问
RUN ldconfig && \
    echo "TDengine libraries installed successfully"

# Set the working directory
WORKDIR /app

# 设置时区
ENV TZ Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 设置pip源为阿里云源
RUN mkdir -p /root/.pip
RUN echo "[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple/\n[install]\ntrusted-host=mirrors.aliyun.com" > /root/.pip/pip.conf


# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app/ .

# Copy the startup script and make it executable
COPY start.sh .
RUN chmod +x start.sh

# Expose the FastAPI port
EXPOSE 8003

# Command to run the application
CMD ["./start.sh"]