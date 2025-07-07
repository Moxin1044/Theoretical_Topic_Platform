FROM python:3.11-slim

WORKDIR /app

# debian 主源和安全源分开写，彻底兼容 bookworm + 清华源
RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/* && \
    echo "Types: deb\nURIs: https://mirrors.tuna.tsinghua.edu.cn/debian/\nSuites: bookworm bookworm-updates bookworm-backports\nComponents: main contrib non-free non-free-firmware" > /etc/apt/sources.list.d/tuna.sources && \
    echo "Types: deb\nURIs: https://mirrors.tuna.tsinghua.edu.cn/debian-security/\nSuites: bookworm-security\nComponents: main contrib non-free non-free-firmware" > /etc/apt/sources.list.d/tuna-security.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev libmariadb-dev pkg-config default-mysql-client python3-flask && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装（使用清华源）
COPY requirements.txt .
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 复制并授权 entrypoint.sh
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

# 设置环境变量
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV DATABASE_URI=mysql+pymysql://root:password@db:3306/theory_db

# 暴露端口
EXPOSE 5000

# 使用 entrypoint.sh 启动应用，实现自动迁移数据库
CMD ["./entrypoint.sh"]