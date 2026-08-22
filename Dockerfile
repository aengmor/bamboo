# 1. 拉取自带 Python 3.10 的精简版 Linux
FROM python:3.13-slim

# 2. 修正：使用等号格式设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. 设置工作目录
WORKDIR /app

# 4. 安装可能需要的 C 编译环境（防止部分包编译失败）
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 5. 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 6. 复制项目代码
COPY . .

# 7. 启动 Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]