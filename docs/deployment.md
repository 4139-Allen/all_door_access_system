# 部署与配置

## 环境变量

### 必填

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `SECRET_KEY` | JWT 签名密钥（至少 32 字符随机字符串） | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `MYSQL_HOST` | MySQL 主机 | Docker: `mysql`，本地: `localhost` |
| `MYSQL_PASSWORD` | MySQL root 密码 | `your-strong-password` |
| `MYSQL_DB` | 数据库名 | `door_access_system` |

### 可选 - 核心

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ALGORITHM` | JWT 算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 有效期（分钟） | `3600` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_USER` | MySQL 用户名 | `root` |
| `AUTO_CREATE_ADMIN` | 启动时自动创建管理员 | `true` |
| `ADMIN_USERNAME` | 默认管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 默认管理员密码 | `123456` |

### 可选 - Redis

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `REDIS_HOST` | Redis 主机 | `127.0.0.1` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_DB` | Redis 数据库编号 | `0` |
| `REDIS_PASSWORD` | Redis 密码（可选） | 无 |

### 可选 - MQTT

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MQTT_BROKER_HOST` | MQTT Broker 主机 | `127.0.0.1` |
| `MQTT_BROKER_PORT` | MQTT Broker 端口 | `1883` |
| `MQTT_TOPIC_PREFIX` | MQTT 主题前缀 | `door` |
| `MQTT_USERNAME` | MQTT 用户名 | 无 |
| `MQTT_PASSWORD` | MQTT 密码 | 无 |

### 可选 - AI（DeepSeek）

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 无（不配置则 AI 功能不可用） |
| `AI_API_URL` | AI API 地址 | `https://api.deepseek.com/v1/chat/completions` |
| `AI_MODEL` | AI 模型名称 | `deepseek-v4-flash` |
| `AI_TIMEOUT` | AI 请求超时（秒） | `15` |
| `AI_TEMPERATURE` | AI 温度参数 | `0.1` |

### 可选 - 微信小程序

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `WX_APPID` | 微信小程序 AppID | 无 |
| `WX_SECRET` | 微信小程序 AppSecret | 无 |

### 可选 - 阿里云短信

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ALIYUN_ACCESS_KEY_ID` | 阿里云 AccessKey ID | 无 |
| `ALIYUN_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret | 无 |
| `ALIYUN_SMS_SIGN` | 短信签名 | 无 |
| `ALIYUN_SMS_TEMPLATE` | 短信模板 Code | 无 |

> 阿里云短信用于验证码登录功能。需在阿里云控制台开通短信服务、申请签名和模板。不配置则短信验证码功能不可用，不影响系统启动。

### 可选 - SMTP 邮件

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SMTP_HOST` | SMTP 服务器地址 | 无 |
| `SMTP_PORT` | SMTP 端口 | `465` |
| `SMTP_USER` | SMTP 用户名 | 无 |
| `SMTP_PASSWORD` | SMTP 密码 | 无 |
| `SMTP_FROM` | 发件人地址 | 无（默认使用 SMTP_USER） |

> SMTP 邮件用于邮箱验证码功能。支持 SSL（端口 465）和 STARTTLS（端口 587）两种加密方式。不配置则邮箱验证码功能不可用，不影响系统启动。

### 可选 - CORS

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ALLOWED_ORIGINS` | CORS 允许来源（逗号分隔） | `http://localhost:5173` |

## 环境区分

### Docker 环境（deploy/.env）

必须使用 Docker Compose 服务名：
```env
MYSQL_HOST=mysql
REDIS_HOST=redis
MQTT_BROKER_HOST=mosquitto
ALLOWED_ORIGINS=http://localhost,http://localhost:80
```

### 本地开发（backend/.env）

使用 localhost：
```env
MYSQL_HOST=localhost
REDIS_HOST=127.0.0.1
MQTT_BROKER_HOST=127.0.0.1
ALLOWED_ORIGINS=http://localhost:5173
```

### 配置文件说明

| 文件 | 位置 | 说明 |
|------|------|------|
| `.env.example` | `deploy/` 和 `backend/` | 环境变量模板（可提交到 Git） |
| `.env.docker` | `deploy/` 和 `backend/` | Docker 环境专用模板 |
| `.env` | `deploy/` 和 `backend/` | 实际配置文件（**不要提交到 Git**） |

> `deploy/.env` 会被 Docker Compose 的 `env_file` 加载，同时 `docker compose.yml` 中的 `environment` 会覆盖主机名相关的变量（`MYSQL_HOST=mysql` 等）。

## Docker 部署

### 服务架构

Docker Compose 编排 5 个服务：

| 服务 | 镜像 | 内部端口 | 外部端口 | 内存限制 | 说明 |
|------|------|---------|---------|----------|------|
| mysql | mysql:8.0 | 3306 | 3307 | 784MB | 数据库（utf8mb4） |
| redis | redis:6 | 6379 | 6379 | 128MB | 缓存 + Token |
| mosquitto | eclipse-mosquitto:2 | 1883 | 1883 | 64MB | MQTT Broker |
| fastapi | 自建 | 8000 | 8000 | 256MB | 后端 API |
| frontend | 自建 (Nginx) | 80/443 | 80/443 | 64MB | 前端 + 反向代理 |

### 数据卷

| 卷名 | 用途 |
|------|------|
| `mysql-data` | MySQL 数据持久化 |
| `redis-data` | Redis 数据持久化 |
| `mosquitto-data` | Mosquitto 数据 |
| `mosquitto-logs` | Mosquitto 日志 |
| `uploads-data` | 上传文件存储 |

### 健康检查

所有服务均配置了健康检查：
- **MySQL**：`mysqladmin ping`，每 10 秒检测，30 秒启动宽限期
- **Redis**：`redis-cli ping`，每 10 秒检测
- **FastAPI**：`curl /health`，每 10 秒检测，20 秒启动宽限期
- FastAPI 依赖 MySQL 和 Redis 健康后才启动，Mosquitto 只需启动即可

### 一键部署脚本

提供 `deploy.sh`（Linux/macOS）和 `deploy.bat`（Windows）：

```bash
# Linux / macOS
cd deploy && bash deploy.sh

# Windows
cd deploy && deploy.bat
```

脚本自动完成：
1. 检查 Docker 和 docker compose 是否安装
2. 从 `.env.docker` 创建 `.env`（如不存在）
3. 创建 `logs/` 目录和 `mosquitto.conf`
4. 停止旧容器
5. 构建并启动所有服务
6. 等待服务就绪并显示状态
7. 显示访问地址和常用命令

### 常用命令

```bash
cd deploy

# 启动全部服务
docker compose up -d

# 首次部署（构建镜像）
docker compose up -d --build

# 重建后端（代码修改后）
docker compose up -d --build fastapi

# 重建前端（代码修改后）
cd ../web && npm run build && cd ../deploy
docker compose up -d --build frontend

# 查看所有服务状态
docker compose ps

# 查看日志（全部）
docker compose logs -f

# 查看指定服务日志
docker compose logs -f fastapi
docker compose logs -f mysql

# 重启单个服务
docker compose restart fastapi

# 停止全部服务
docker compose down

# 完全重置（清空数据库数据）
docker compose down -v
docker compose up -d --build
```

## 前端构建

Web 前端必须在 Docker 部署前构建：

```bash
cd web
npm install
npm run build
# 生成 dist/ 目录，Dockerfile.frontend 会将其打包到 Nginx 镜像
```

Nginx 配置（`web/nginx.conf`）处理：
- Vue Router history 模式的 `try_files` 回退
- `/api/` 反向代理到 FastAPI 后端
- `/ws` WebSocket 代理
- SSL 证书配置（doorlink.top）

## SSL 证书

生产环境 SSL 证书存放在 `SSL/` 目录：

```
SSL/
├── doorlink.top.pem    # 证书文件
└── doorlink.top.key    # 私钥文件
```

Docker Compose 通过 volume 挂载到 Nginx 容器：
```yaml
volumes:
  - ../SSL/doorlink.top.pem:/etc/nginx/ssl/doorlink.top.pem:ro
  - ../SSL/doorlink.top.key:/etc/nginx/ssl/doorlink.top.key:ro
```

## 系统初始化

FastAPI 启动时自动执行以下初始化（`main.py` lifespan）：

1. **数据库初始化**：创建所有表（如果不存在）
2. **管理员创建**：根据 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 创建默认管理员（`AUTO_CREATE_ADMIN=true` 时）
3. **权限初始化**：创建默认角色（admin/user）和权限，为管理员分配所有权限
4. **设备状态重置**：将所有设备标记为 offline（Redis 缓存重启后丢失）

## 常见问题

### 1. 数据库连接失败
```
❌ 缺少数据库配置：MYSQL_HOST, MYSQL_PASSWORD, MYSQL_DB
```
**原因**：`.env` 文件缺失或配置错误
**解决**：
- Docker 环境：确保 `MYSQL_HOST=mysql`（不是 localhost）
- 本地开发：确保 `MYSQL_HOST=localhost`，MySQL 已启动
- 检查 `MYSQL_PASSWORD` 和 `MYSQL_DB` 是否正确

### 2. 前端页面空白
**原因**：前端未构建或 Nginx 配置错误
**解决**：
```bash
cd web && npm run build
cd ../deploy && docker compose up -d --build frontend
docker compose logs frontend
```

### 3. 后端 502 Bad Gateway
**原因**：FastAPI 服务未启动或崩溃
**解决**：
```bash
docker compose ps fastapi        # 检查状态
docker compose logs fastapi      # 查看错误日志
docker compose restart fastapi   # 重启服务
```

### 4. AI 功能不工作
**原因**：未配置 DeepSeek API Key 或网络不通
**解决**：
- 在 `.env` 中配置 `DEEPSEEK_API_KEY`
- 确认服务器可访问 `api.deepseek.com`
- 检查日志中的警告信息

### 5. MQTT 连接失败
**原因**：Mosquitto Broker 未启动或配置错误
**解决**：
- Docker：`docker compose ps mosquitto`，检查 `mosquitto.conf` 是否正确挂载
- 本地：确保 Mosquitto 已启动（`mosquitto -v`）
- 检查 `MQTT_BROKER_HOST` 配置

### 6. 设备离线
**原因**：设备心跳超时或 MQTT 连接中断
**解决**：
- 检查设备固件 MQTT 配置（Broker 地址、端口、用户名/密码）
- 设备在线状态 Redis 缓存 70 秒过期，等待自动恢复
- 查看后端日志中是否有设备上线记录

### 7. 用户/设备删除失败
**原因**：存在关联数据
**解决**：需先解绑所有关联关系
- 删除用户前：先解绑其所有设备（`DELETE /devices/{id}/unbind?user_id=`）
- 删除设备前：先解绑所有绑定用户

### 8. Token 过期 / 频繁登录
**原因**：Token 有效期到期
**解决**：
- 默认有效期 3600 分钟（60 小时）
- 调整 `ACCESS_TOKEN_EXPIRE_MINUTES` 环境变量
- 退出登录会立即使 Token 失效（加入黑名单）

### 9. 短信验证码发送失败
**原因**：阿里云短信未配置或余额不足
**解决**：
- 配置 `ALIYUN_ACCESS_KEY_ID`、`ALIYUN_ACCESS_KEY_SECRET`
- 配置 `ALIYUN_SMS_SIGN`（短信签名）和 `ALIYUN_SMS_TEMPLATE`（模板 Code）
- 检查阿里云短信服务余额和模板审核状态

### 10. Redis 连接失败
**原因**：Redis 未启动或配置错误
**解决**：
- 系统会在无 Redis 时降级运行（缓存和 Token 管理不可用）
- Docker：`docker compose ps redis`
- 本地：启动 `redis-server`
- 如需密码认证：配置 `REDIS_PASSWORD`

### 11. 运行测试
```bash
cd backend

# 全部测试
pytest tests/ -v

# 指定模块
pytest tests/test_auth.py -v

# 覆盖率报告
pytest tests/ --cov=. --cov-report=html

# 覆盖率摘要
pytest tests/ --cov=. --cov-report=term-missing
```
