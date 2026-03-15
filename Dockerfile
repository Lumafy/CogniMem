FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（编译 psycopg 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# 启动服务
CMD ["python3", "-m", "cognimem.cli", "serve", \
     "--db", "./data/memory.db", \
     "--host", "0.0.0.0", \
     "--port", "8000"]
