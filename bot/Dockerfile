FROM python:3.11-slim

WORKDIR /app


# 复制代码
COPY requirements.txt /app
COPY bot/telegram_bot.py /app/bot/telegram_bot.py
COPY common/ /app/common

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# 运行机器人
CMD ["python", "bot/telegram_bot.py"] 