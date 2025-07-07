# PowerShell 脚本
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
cd $PSScriptRoot

# 创建虚拟环境（如不存在）
if (!(Test-Path ".venv")) {
    python -m venv .venv
}

# 激活虚拟环境
. .venv\Scripts\Activate.ps1

# 安装依赖（清华源）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 升级数据库
flask db upgrade

# 启动应用
python app.py 