#!/bin/bash

# 等待 MySQL 服务可用
until mysqladmin ping -h"db" -P"3306" -u"root" -ppassword --silent; do
  echo "Waiting for MySQL..."
  sleep 2
done

# 自动迁移数据库
flask db upgrade

# 自动创建admin用户
python -c "from app import ensure_admin_user; ensure_admin_user()"

# 启动 gunicorn
exec gunicorn --bind 0.0.0.0:5000 app:app 