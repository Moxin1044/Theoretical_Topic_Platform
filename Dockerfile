FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev libmysqlclient-dev && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 设置环境变量
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV DATABASE_URI=mysql+pymysql://root:password@db:3306/theory_db

# 暴露端口
EXPOSE 5000

# 使用gunicorn启动应用
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]