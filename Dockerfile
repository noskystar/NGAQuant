FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p data logs output

# 暴露端口（Web界面）
EXPOSE 8501

# 环境变量
ENV PYTHONPATH=/app
ENV KIMI_API_KEY=""
ENV FEISHU_WEBHOOK=""

# 默认启动命令
CMD ["python", "cli.py", "--help"]
