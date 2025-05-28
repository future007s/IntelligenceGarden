FROM python:3.12.6

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