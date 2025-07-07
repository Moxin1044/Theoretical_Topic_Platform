@echo off
cd /d %~dp0

REM 创建虚拟环境（如不存在）
if not exist .venv (
    python -m venv .venv
)

REM 激活虚拟环境
call .venv\Scripts\activate.bat

REM 安装依赖（清华源）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

REM 升级数据库
flask db upgrade

REM 启动应用
python app.py 