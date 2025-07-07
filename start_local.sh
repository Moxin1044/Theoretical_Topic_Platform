#!/bin/bash

# 进入项目目录
cd "$(dirname "$0")"

# 创建虚拟环境（如不存在）
if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖（使用清华源）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 初始化数据库（如未创建）
if [ ! -f "app.db" ]; then
  flask db upgrade
fi

# 再次升级数据库，确保最新
flask db upgrade

# 启动应用
python app.py 