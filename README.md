# Theoretical Topic Platform

## 项目简介

本项目为理论题库平台，支持题目、试卷、用户的管理，适合教学、考试等场景。

## 功能特性
- 用户登录、登出
- 管理员后台：
  - 题目管理（增删改查、导入导出）
  - 试卷管理（增删改查）
  - 用户管理（增删改查、重置密码）
- 普通用户可浏览试卷、题目
- 支持 Docker 部署

## 用户管理
- 管理员可在"后台-用户管理"页面对用户进行增删改查、重置密码操作。
- 用户可在"修改密码"页面修改自己的密码。

## 默认管理员账号
- 用户名：admin
- 密码：admin123

> Docker 启动时会自动创建该账号（如不存在）。

## 部署与运行

### 1. 本地运行

#### 终端命令添加 Docker 镜像加速

```bash
# 将内容写入 /etc/docker/daemon.json 文件，root 用户可以去掉 sudo
# 配置 Docker 镜像，使用多个镜像源来提高镜像下载速度
echo '{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.1panel.live",
    "https://docker.ketches.cn"
  ]
}' | sudo tee /etc/docker/daemon.json
# 重启 Docker 服务以使配置生效
sudo systemctl restart docker
```

```bash
pip install -r requirements.txt
export FLASK_APP=app.py
flask db upgrade  # 初始化数据库
flask run
```

### 2. Docker 部署

```bash
docker build -t theoretical-topic-platform .
docker-compose up -d
```

### 3. 访问
- 前台：http://localhost:5000/
- 后台：http://localhost:5000/admin

## 重要接口说明

- 用户管理 API：
  - GET    /admin/api/users
  - POST   /api/user
  - PUT    /api/user/<id>
  - DELETE /api/user/<id>
- 修改密码 API：
  - POST   /api/user/change_password

## 其他
- 如需自定义管理员账号，请修改 `app.py` 中的自动创建逻辑。
- 题库、试卷等功能详见后台页面。 