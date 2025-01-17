FROM python:3.11-slim

WORKDIR /app



# 复制代码
COPY requirements.txt /app
COPY spiders/ /app/spiders
COPY common/ /app/common

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://repo.huaweicloud.com/artifactory/pypi-public/simple/ \
    PIP_TRUSTED_HOST=repo.huaweicloud.com

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt    

# 运行爬虫
CMD ["python", "spiders/main.py"] 