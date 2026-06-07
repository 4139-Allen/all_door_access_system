# API 文档

基础路径：`/api`

完整交互式文档：`http://localhost:8000/docs`（Swagger UI）/ `http://localhost:8000/redoc`（ReDoc）

## 认证接口

| 方法 | 路径 | 描述 | 权限 | 限流 |
|------|------|------|------|------|
| POST | `/auth/login` | 用户登录（用户名+密码） | 公开 | 5 次/60s |
| POST | `/auth/register` | 用户注册（创建普通用户） | 公开 | - |
| POST | `/auth/logout` | 退出登录（Token 加入黑名单） | 已认证 | - |
| PUT | `/auth/password` | 修改当前用户密码 | 已认证 | - |
| POST | `/auth/wx-login` | 微信小程序登录（code → JWT） | 公开 | - |
| PUT | `/auth/wx-bind` | 绑定已有账号到微信 | 已认证 | - |

### 登录请求示例

```json
POST /api/auth/login
{
  "username": "admin",
  "password": "123456"
}

// 响应
{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "role": "admin",
    "username": "admin"
  }
}
```

### 修改密码请求示例

```json
PUT /api/auth/password
Authorization: Bearer <token>
{
  "old_password": "123456",
  "new_password": "newpassword123"
}
```

## 用户管理（需 `user.manage` 权限）

| 方法 | 路径 | 描述 | 参数 |
|------|------|------|------|
| GET | `/users` | 用户列表 | `page`, `size`, `username`, `role`（分页+筛选） |
| POST | `/users` | 创建用户 | Body: `{username, password, role}` |
| DELETE | `/users/{user_id}` | 删除用户（需先解绑设备） | Path: `user_id` |
| GET | `/users/{user_id}/devices` | 查询用户绑定的设备列表 | Path: `user_id` |

### 用户列表请求示例

```
GET /api/users?page=1&size=10&username=&role=
Authorization: Bearer <token>

// 响应
{
  "code": 200,
  "msg": "查询成功",
  "data": {
    "total": 25,
    "items": [
      {"id": 1, "username": "admin", "role": "admin", "created_at": "2026-01-01 00:00:00"},
      {"id": 2, "username": "user1", "role": "user", "created_at": "2026-01-02 10:30:00"}
    ]
  }
}
```

## 设备管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/devices` | 创建设备 | `device.manage` |
| GET | `/devices` | 设备列表（按权限过滤） | 已认证 |
| PUT | `/devices/{device_id}` | 更新设备信息 | `device.manage` |
| DELETE | `/devices/{device_id}` | 删除设备（需先解绑用户） | `device.manage` |
| POST | `/devices/{device_id}/bind` | 绑定用户到设备 | `device.manage` |
| DELETE | `/devices/{device_id}/unbind` | 解绑用户与设备 | `device.manage` |

### 设备列表说明
- **管理员**：查看所有设备
- **普通用户**：仅查看已绑定的设备
- 设备列表 Redis 缓存 60 秒，CRUD 操作后自动失效

### 绑定/解绑请求示例

```json
// 绑定
POST /api/devices/1/bind
Authorization: Bearer <token>
{"user_id": 2}

// 解绑
DELETE /api/devices/1/unbind?user_id=2
Authorization: Bearer <token>
```

## 门禁控制

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/doors/{device_id}/open` | 开启门禁（含权限校验） | 已认证 |
| GET | `/door-logs` | 查询开门日志 | 已认证 |

### 开门权限规则
- **管理员**：可开启任意设备
- **普通用户**：仅可开启已绑定的设备
- 开门指令通过 MQTT QoS 1 发送到设备

### 开门请求示例

```json
POST /api/doors/1/open
Authorization: Bearer <token>

// 响应
{"code": 200, "msg": "开门指令已发送", "data": null}
```

### 日志查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码（默认 1） |
| `size` | int | 每页条数（默认 10） |
| `user_id` | int | 按用户 ID 筛选（管理员可查全部） |
| `device_name` | str | 按设备编号模糊搜索 |
| `status` | str | 按状态筛选（成功/失败） |
| `start_time` | str | 起始时间（YYYY-MM-DD HH:MM:SS） |
| `end_time` | str | 结束时间（YYYY-MM-DD HH:MM:SS） |

## 权限管理（需 `user.manage` 权限）

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/permissions` | 获取所有权限（按模块分组） |
| GET | `/roles` | 获取所有角色及权限 |
| POST | `/roles` | 创建自定义角色 |
| PUT | `/roles/{role_id}` | 修改角色名称 |
| DELETE | `/roles/{role_id}` | 删除自定义角色（系统角色不可删） |
| PUT | `/roles/{role_id}/permissions` | 设置角色权限 |

### 权限列表响应示例

```json
GET /api/permissions
Authorization: Bearer <token>

{
  "code": 200,
  "msg": "查询成功",
  "data": [
    {
      "module": "用户",
      "permissions": [
        {"id": 1, "code": "user.manage", "name": "用户管理"}
      ]
    },
    {
      "module": "设备",
      "permissions": [
        {"id": 2, "code": "device.manage", "name": "设备管理"}
      ]
    },
    {
      "module": "门禁",
      "permissions": [
        {"id": 3, "code": "door.open", "name": "远程开门"},
        {"id": 4, "code": "door.log", "name": "开门日志"}
      ]
    }
  ]
}
```

### 设置角色权限请求示例

```json
PUT /api/roles/2/permissions
Authorization: Bearer <token>
{
  "permission_ids": [1, 3, 4]
}
```

## 统计

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/statistics` | 获取统计数据（角色区分） | 已认证 |

### 统计数据说明
- **管理员**：全局统计（总用户数、总设备数、今日开门次数、总开门次数等）
- **普通用户**：个人统计（绑定设备数、个人开门次数等）
- 统计数据 Redis 缓存 180 秒

## AI 助手（需 `admin` 角色）

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/ai/chat` | AI 对话（开门 + 数据查询） | 管理员 |

### AI 对话请求示例

```json
POST /api/ai/chat
Authorization: Bearer <token>
{
  "message": "帮我打开 001 号门"
}

// 响应
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "reply": "已为您打开 001 号门（大门）",
    "action_taken": true
  }
}
```

### AI 功能说明
- 支持自然语言开门（如"打开大门"、"开 001 号门"）
- 支持数据查询（如"今天开了几次门"、"有多少设备"）
- 对话上下文 Redis 缓存 15 分钟，支持多轮对话
- 成功开门后自动清除对话上下文
- 需配置 `DEEPSEEK_API_KEY` 环境变量

## WebSocket 实时通知

连接地址：`ws://host/ws`

### 认证流程

1. 客户端建立 WebSocket 连接
2. 客户端发送认证消息：`{"type": "auth", "token": "<JWT_TOKEN>"}`
3. 服务端验证 JWT（10 秒超时，超时断开）
4. 认证成功后，拥有对应权限的管理员接收实时通知

### 消息类型

#### 开门事件通知
```json
{
  "type": "door_open",
  "message": "【用户A】打开了【001号门禁】(大门入口)",
  "username": "用户A",
  "device_name": "001号门禁",
  "location": "大门入口",
  "action": "远程开门",
  "timestamp": "2026-06-07 14:30:00",
  "device_id": 1
}
```

#### 设备状态变更通知
```json
{
  "type": "device_status",
  "device_id": 1,
  "device_name": "001号门禁",
  "status": "online",       // 或 "offline"
  "location": "大门入口"
}
```

#### 心跳检测
```json
// 客户端发送
{"type": "ping"}

// 服务端响应
{"type": "pong"}
```

### 权限说明
- 拥有 `door.open` 权限的管理员：接收开门事件通知
- 拥有 `device.manage` 权限的管理员：接收设备状态变更通知
- 普通用户：不接收推送通知

## 健康检查

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/health` | 系统健康检查 | 公开 |

```json
GET /health

{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

## 统一响应格式

```json
// 成功响应
{
  "code": 200,
  "msg": "操作成功",
  "data": { ... }
}

// 错误响应
{
  "code": 400,
  "msg": "错误信息",
  "data": null
}

// 分页响应
{
  "code": 200,
  "msg": "查询成功",
  "data": {
    "total": 100,
    "items": [ ... ]
  }
}
```

### 错误码说明

| HTTP 状态码 | 场景 |
|------------|------|
| 400 | 参数校验失败 / 业务逻辑错误 |
| 401 | 未认证 / Token 无效 / Token 过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 429 | 请求频率过高（限流） |
| 500 | 服务器内部错误 |
| 504 | 请求超时 |

## 认证方式

所有需认证的接口在请求头中携带 Token：

```
Authorization: Bearer <JWT_TOKEN>
```

Token 有效期默认 3600 分钟（可通过 `ACCESS_TOKEN_EXPIRE_MINUTES` 配置），退出登录后 Token 加入黑名单立即失效。
