# 使用官方 Python 瘦身镜像（基于 Debian）
FROM python:3.9-slim

# 设置容器内工作目录
WORKDIR /app

# 先单独复制依赖声明文件（利用 Docker 缓存层）
COPY requirements.txt .

# 安装系统依赖（按需补充）及处理换行符工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    dos2unix \
    # 安装 Python 包编译依赖（按需补充示例）：
    # gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（生产环境推荐使用固定版本）
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码（放在后面以充分利用缓存层）
COPY . .

# 转换 Windows 换行符为 UNIX 格式（防止 format error）
RUN dos2unix start.sh && \
    # 确保脚本可执行（冗余操作，但双重确认）
    chmod +x start.sh

# 验证脚本解释器（如果使用 bash 需额外安装）
# RUN apt-get update && apt-get install -y --no-install-recommends bash

# 设置环境变量（建议敏感信息通过运行时传递）
ENV RINNAI_USERNAME="phone" \
    RINNAI_PASSWORD="password" \
    LOCAL_MQTT_HOST="localhost" \
    LOCAL_MQTT_PORT="1883"

# 使用非 root 用户运行（安全增强）
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 推荐显式指定解释器执行脚本
CMD ["sh", "start.sh"]