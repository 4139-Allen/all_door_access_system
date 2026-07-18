# API 文档

基础路径：`/api`

完整交互式文档：`http://localhost:8000/docs`（Swagger UI）/ `http://localhost:8000/redoc`（ReDoc）

---

## 目录

- [认证接口](#认证接口)
- [微信小程序认证](#微信小程序认证)
- [用户管理](#用户管理-需-user-view-权限)
- [设备管理](#设备管理)
- [门禁控制](#门禁控制)
- [异常事件](#异常事件)
- [权限管理](#权限管理-需-user-manage-权限)
- [统计](#统计)
- [AI 指令开门](#ai-指令开门)
- [WebSocket 实时通知](#websocket-实时通知)
- [健康检查](#健康检查)
- [统一响应格式](#统一响应格式)
- [错误码说明](#错误码说明)
- [认证方式](#认证方式)

---

## 认证接口

| 方法 | 路径 | 描述 | 权限 | 限流 |
|------|------|------|------|------|
| POST | `/auth/login` | 用户登录（用户名+密码） | 公开 | 5 次/60s |
| POST | `/auth/register` | 用户注册（创建普通用户） | 公开 | 5 次/60s |
| POST | `/auth/send-code` | 发送验证码（手机号或邮箱） | 公开 | 5 次/60s |
| POST | `/auth/login-phone` | 手机号+验证码登录 | 公开 | 5 次/60s |
| POST | `/auth/login-email` | 邮箱+验证码登录 | 公开 | 5 次/60s |
| POST | `/auth/logout` | 退出登录（Token 加入黑名单） | 已认证 | - |
| PUT | `/auth/password` | 修改当前用户密码 | 已认证 | - |
| POST | `/auth/reset-password` | 忘记密码（手机号+验证码重置） | 公开 | 5 次/60s |
| GET | `/auth/profile` | 获取个人信息 | 已认证 | - |
| PUT | `/auth/profile` | 修改用户名 | 已认证 | - |
| PUT | `/auth/avatar` | 上传头像 | 已认证 | - |

### 登录请求示例

```json
POST /api/auth/login
{
  "username": "admin",
  "password": "123456"
}

// 响应（⚠️ Token 仅在响应头中，不在响应体）
// Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "role": "admin",
    "username": "admin",
    "avatar": null,
    "permissions": ["user.view", "user.manage", "door.open", ...]
  }
}
```

### 发送验证码

```json
POST /api/auth/send-code
{
  "target": "13800138000"     // 手机号或邮箱
}

// 响应
{
  "code": 200,
  "msg": "验证码已发送",
  "data": null
}
```

### 手机号 / 邮箱登录

```json
POST /api/auth/login-phone
{
  "phone": "13800138000",
  "code": "123456"            // 6位验证码
}

// 响应（⚠️ Token 仅在响应头 Authorization 中）
// Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "role": "admin",
    "username": "admin",
    "avatar": null,
    "permissions": [...]
  }
}
```

```json
POST /api/auth/login-email
{
  "email": "admin@example.com",
  "code": "123456"
}

// 响应同上（Token 仅在响应头）
```

### 修改密码

```json
PUT /api/auth/password
Authorization: Bearer <token>
{
  "old_password": "123456",
  "new_password": "newpassword123"
}

// 响应
{"code": 200, "msg": "密码修改成功", "data": null}
```

### 忘记密码

```json
POST /api/auth/reset-password
{
  "phone": "13800138000",
  "code": "123456",
  "new_password": "newpassword123"
}

// 响应
{"code": 200, "msg": "密码重置成功", "data": null}
```

### 获取个人信息

```json
GET /api/auth/profile
Authorization: Bearer <token>

// 响应
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "phone": "138****8000",
    "avatar": "http://host/uploads/avatars/xxx.jpg",
    "created_at": "2026-01-01 00:00:00"
  }
}
```

### 修改用户名

```json
PUT /api/auth/profile
Authorization: Bearer <token>
{
  "username": "new_username"
}

// 响应
{"code": 200, "msg": "用户名修改成功", "data": null}
```

### 上传头像

```
PUT /api/auth/avatar
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <图片文件>

// 响应
{
  "code": 200,
  "msg": "头像上传成功",
  "data": {
    "avatar": "http://host/uploads/avatars/xxx.jpg"
  }
}
```

---

## 微信小程序认证

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/auth/wx-login` | 微信小程序登录（code → JWT） | 公开 |
| PUT | `/auth/wx-bind` | 绑定已有账号到微信 | 已认证 |

```json
POST /api/auth/wx-login
{
  "code": "wx_login_code"
}

// 响应（⚠️ Token 仅在响应头 Authorization 中）
// Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "role": "user",
    "username": "wechat_user",
    "avatar": null,
    "permissions": [...]
  }
}
```

```json
PUT /api/auth/wx-bind
Authorization: Bearer <token>
{
  "username": "admin",
  "password": "123456"
}

// 响应（⚠️ 返回新 Token，仅在响应头）
// Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
{
  "code": 200,
  "msg": "绑定成功",
  "data": {
    "role": "admin",
    "username": "admin",
    "avatar": null,
    "permissions": [...]
  }
}
```

---

## 用户管理（需 `user.view` / `user.manage` 权限）

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/users` | 用户列表（分页+筛选） | `user.view` |
| POST | `/users` | 创建用户 | `user.manage` |
| PUT | `/users/{user_id}/role` | 修改用户角色 | `user.manage` |
| POST | `/users/import` | 批量导入用户（Excel） | `user.manage` |
| DELETE | `/users/{user_id}` | 删除用户（需先解绑设备） | `user.manage` |
| GET | `/users/{user_id}/devices` | 查询用户绑定的设备列表 | `user.view` |

### 用户列表请求参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码（默认 1） |
| `size` | int | 每页条数（默认 10） |
| `username` | str | 用户名模糊搜索（可选） |
| `role` | str | 角色筛选：`admin` / `operator` / `user`（可选） |

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

### 创建用户

```json
POST /api/users
Authorization: Bearer <token>
{
  "username": "newuser",
  "password": "123456",
  "role": "user"              // 可选：user, operator, admin（默认 user）
}

// 响应
{
  "code": 200,
  "msg": "创建成功",
  "data": {
    "id": 3,
    "username": "newuser",
    "role": "user"
  }
}
```

### 修改用户角色

```json
PUT /api/users/3/role
Authorization: Bearer <token>
{
  "role": "operator"
}

// 响应
{"code": 200, "msg": "角色修改成功", "data": null}
```

### 批量导入用户

```
POST /api/users/import
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <Excel 文件>

// 响应
{"code": 200, "msg": "成功导入 10 个用户（失败 0 个）", "data": ...}
```

---

## 设备管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/devices` | 新增设备 | `device.create` |
| GET | `/devices` | 设备列表（分页+筛选） | `device.view` 或 `door.open` |
| PUT | `/devices/{device_id}` | 更新设备信息 | `device.edit` |
| DELETE | `/devices/{device_id}` | 删除设备（需先解绑用户） | `device.delete` |
| POST | `/devices/{device_id}/bind` | 绑定用户到设备 | `device.bind` |
| DELETE | `/devices/{device_id}/unbind` | 解绑用户与设备 | `device.bind` |

### 设备列表请求参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码（默认 1） |
| `size` | int | 每页条数（默认 10） |
| `name` | str | 设备名称模糊搜索（可选） |

### 设备列表说明
- 拥有 `device.view` 权限：查看所有设备
- 仅拥有 `door.open` 权限：仅查看已绑定的设备
- 设备列表 Redis 缓存 60 秒，CRUD 操作后自动失效

### 创建设备

```json
POST /api/devices
Authorization: Bearer <token>
{
  "name": "001",
  "location": "大门入口"
}

// 响应
{"code": 200, "msg": "创建设备成功", "data": {"device_id": 1}}
```

### 更新设备

```json
PUT /api/devices/1
Authorization: Bearer <token>
{
  "name": "大门-001",
  "status": "online",          // "online" 或 "offline"
  "location": "公司正门"
}

// 响应
{"code": 200, "msg": "更新成功", "data": null}
```

### 绑定/解绑

```json
// 绑定
POST /api/devices/1/bind
Authorization: Bearer <token>
{"user_id": 2}

// 响应
{"code": 200, "msg": "绑定成功", "data": null}

// 解绑（204 No Content）
DELETE /api/devices/1/unbind?user_id=2
Authorization: Bearer <token>
```

---

## 门禁控制

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/doors/{device_id}/open` | 开启门禁（含权限校验） | `door.open` |
| GET | `/door-logs` | 查询开门日志（分页+筛选） | `door.view_own_log` |

### 开门权限规则
- 拥有 `door.open` 权限：可开启任意设备
- 普通用户：仅可开启已绑定的设备
- 开门指令通过 MQTT QoS 1 发送到设备
- 成功开门后异步发送 WebSocket 通知

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
| `page` | int | 页码（默认 1，范围 1-100） |
| `size` | int | 每页条数（默认 10，最大 100） |
| `user_id` | int | 按用户 ID 筛选（管理员可查全部） |
| `device_name` | str | 按设备编号模糊搜索 |
| `status` | str | 按状态筛选（支持前缀匹配，如"失败"匹配"失败：无权限"） |
| `start_time` | datetime | 起始时间（YYYY-MM-DD HH:MM:SS） |
| `end_time` | datetime | 结束时间（YYYY-MM-DD HH:MM:SS） |

```json
// 响应
{
  "code": 200,
  "msg": "获取日志成功",
  "data": {
    "total": 100,
    "list": [
      {
        "id": 1,
        "user_id": 1,
        "username": "admin",
        "device_id": 1,
        "device_name": "001",
        "action": "远程开门",
        "status": "成功",
        "time": "2026-07-17 14:30:00"
      }
    ]
  }
}
```

---

## 异常事件

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/alerts` | 获取异常事件列表（分页+筛选） | `alert.view` |
| GET | `/alerts/stats` | 获取异常事件统计 | `alert.view` |
| POST | `/alerts/unlock/{device_name}` | 解除设备锁定 | `alert.unlock` |

### 异常事件列表参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码（默认 1） |
| `size` | int | 每页条数（默认 10，最大 100） |
| `device_name` | str | 按设备编号模糊搜索 |
| `alert_type` | str | 事件类型：`lock`（锁定）、`offline`（离线）、`error`（失败） |
| `start_time` | str | 起始时间（YYYY-MM-DD HH:MM:SS） |
| `end_time` | str | 结束时间（YYYY-MM-DD HH:MM:SS） |

### 异常事件列表响应示例

```json
GET /api/alerts?page=1&size=10&alert_type=lock
Authorization: Bearer <token>

{
  "code": 200,
  "msg": "查询成功",
  "data": {
    "total": 3,
    "list": [
      {
        "id": 42,
        "user_id": null,
        "username": "本地",
        "device_id": 1,
        "device_name": "001",
        "device_location": "大门入口",
        "action": "密码开锁",
        "status": "密码错误5次，设备锁定5分钟",
        "event_type": "lock",
        "event_level": "danger",
        "ip": "",
        "time": "2026-06-07 14:30:00"
      }
    ]
  }
}
```

### 异常事件统计响应示例

```json
GET /api/alerts/stats?hours=24
Authorization: Bearer <token>

{
  "code": 200,
  "msg": "查询成功",
  "data": {
    "total_alerts": 15,
    "lock_count": 3,
    "error_count": 12,
    "device_stats": [
      {"name": "001", "count": 8},
      {"name": "002", "count": 7}
    ],
    "locked_devices": [
      {
        "device_id": 1,
        "device_name": "001",
        "device_location": "大门入口",
        "lock_ttl": 285
      }
    ],
    "time_range_hours": 24
  }
}
```

### 设备自动锁定规则

| 验证方式 | 错误消息 | 锁定条件 | 锁定时长 |
|----------|----------|----------|----------|
| 密码 | `PWD_ERR` | 连续 5 次错误 | 5 分钟 |
| 指纹 | `FP_ERR` | 连续 5 次错误 | 5 分钟 |
| 刷卡 | `CARD_ERR` | 连续 5 次错误 | 5 分钟 |

- 锁定计数 Redis 键：`door:err:fail:{device_name}`（TTL 300 秒）
- 锁定状态 Redis 键：`door:err:lock:{device_name}`（TTL 300 秒）
- 验证成功自动重置计数：`PWD_OK` / `FP_OK` / `CARD_OK`
- 解除锁定：清除 Redis 键 + 发送 `UNLOCK` MQTT 命令

### 解除设备锁定请求示例

```json
POST /api/alerts/unlock/001
Authorization: Bearer <token>

// 响应
{
  "code": 200,
  "msg": "设备 001 锁定已解除",
  "data": null
}
```

---

## 权限管理（需 `user.manage` 权限）

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/permissions` | 获取所有权限（按模块分组） |
| GET | `/roles` | 获取所有角色及权限 |
| POST | `/roles` | 创建自定义角色 |
| PUT | `/roles/{role_id}` | 修改角色名称 |
| DELETE | `/roles/{role_id}` | 删除自定义角色（系统角色不可删） |
| PUT | `/roles/{role_id}/permissions` | 设置角色权限（全量替换） |

### 创建角色

```json
POST /api/roles
Authorization: Bearer <token>
{
  "name": "安保员",
  "code": "security"
}

// 响应
{"code": 200, "msg": "创建成功", "data": {"id": 5, "name": "安保员", "code": "security"}}
```

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
        {"id": 1, "code": "user.view", "name": "查看用户"},
        {"id": 2, "code": "user.manage", "name": "用户管理"}
      ]
    },
    {
      "module": "设备",
      "permissions": [
        {"id": 3, "code": "device.create", "name": "新增设备"},
        {"id": 4, "code": "device.edit", "name": "编辑设备"},
        {"id": 5, "code": "device.delete", "name": "删除设备"},
        {"id": 6, "code": "device.view", "name": "查看设备"},
        {"id": 7, "code": "device.bind", "name": "绑定/解绑设备"}
      ]
    },
    {
      "module": "门禁",
      "permissions": [
        {"id": 8, "code": "door.open", "name": "远程开门"},
        {"id": 9, "code": "door.view_own_log", "name": "查看开门日志"}
      ]
    },
    {
      "module": "仪表盘",
      "permissions": [
        {"id": 10, "code": "dashboard.view", "name": "查看统计数据"}
      ]
    },
    {
      "module": "异常事件",
      "permissions": [
        {"id": 11, "code": "alert.view", "name": "查看异常事件"},
        {"id": 12, "code": "alert.unlock", "name": "解除设备锁定"}
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
  "permission_ids": [3, 4, 8]
}

// 响应
{"code": 200, "msg": "权限设置成功", "data": null}
```

---

## 统计

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/statistics` | 获取统计数据（角色区分） | `dashboard.view` |
| GET | `/statistics/trend` | 本周开锁趋势（按天统计） | `dashboard.view` |
| GET | `/statistics/actions` | 开锁方式占比分布 | `dashboard.view` |

### 统计数据说明
- **管理员**：全局统计（总用户数、总设备数、今日开门次数、总开门次数等）
- **普通用户**：个人统计（绑定设备数、个人开门次数等）
- 统计数据 Redis 缓存 180 秒

### 统计数据响应示例

```json
GET /api/statistics
Authorization: Bearer <token>

{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "total_users": 25,
    "total_devices": 10,
    "today_open_count": 42,
    "total_open_count": 3680,
    "online_devices": 8,
    "offline_devices": 2
  }
}
```

### 本周趋势响应示例

```json
GET /api/statistics/trend
Authorization: Bearer <token>

{
  "code": 200,
  "msg": "操作成功",
  "data": [
    {"date": "07-11", "count": 12},
    {"date": "07-12", "count": 18},
    {"date": "07-13", "count": 25},
    {"date": "07-14", "count": 8},
    {"date": "07-15", "count": 30},
    {"date": "07-16", "count": 22},
    {"date": "07-17", "count": 15}
  ]
}
```

### 开锁方式占比响应示例

```json
GET /api/statistics/actions
Authorization: Bearer <token>

{
  "code": 200,
  "msg": "操作成功",
  "data": [
    {"name": "远程开门", "value": 120},
    {"name": "密码开锁", "value": 80},
    {"name": "指纹开锁", "value": 45}
  ]
}
```

---

## AI 指令开门

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/ai/chat` | AI 智能开门（自然语言控制门禁） | `door.open` + `device.view` |

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
- 要求用户同时拥有 `door.open` 和 `device.view` 权限

---

## WebSocket 实时通知

连接地址：`ws://host/ws`

### 认证流程

1. 客户端建立 WebSocket 连接
2. 客户端发送认证消息：`{"type": "auth", "token": "<JWT_TOKEN>"}`
3. 服务端验证 JWT（10 秒超时，超时断开）
4. 认证成功后，根据权限接收实时通知

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
  "timestamp": "2026-07-17 14:30:00",
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

#### 设备锁定通知
```json
{
  "type": "device_locked",
  "device_name": "001",
  "device_location": "大门入口",
  "lock_ttl": 300,
  "reason": "密码错误5次，设备锁定5分钟",
  "timestamp": "2026-07-17 14:30:00"
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
- 拥有 `door.open` 权限的用户：接收开门事件通知
- 拥有 `device.view` / `device.edit` 权限的用户：接收设备状态变更通知
- 拥有 `alert.view` 权限的用户：接收设备锁定通知
- 普通用户：不接收推送通知

---

## 健康检查

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/health` | 系统健康检查（检测 MySQL + Redis 连通性） | 公开 |

```json
GET /api/health

// 正常响应
{
  "status": "healthy",
  "service": "door_access_system",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}

// 降级响应（某个依赖不可用）
{
  "status": "degraded",
  "service": "door_access_system",
  "checks": {
    "database": "ok",
    "redis": "error: no connection"
  }
}
// HTTP 状态码：200（healthy）或 503（degraded）
```

---

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
    "items": [ ... ]        // 部分接口使用 "list"
  }
}

// 删除成功（204 No Content，无响应体）
DELETE /api/devices/1
Authorization: Bearer <token>
// HTTP 204 No Content
```

---

## 错误码说明

| HTTP 状态码 | 场景 |
|------------|------|
| 400 | 参数校验失败 / 业务逻辑错误 |
| 401 | 未认证 / Token 无效 / Token 过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 429 | 请求频率过高（限流） |
| 500 | 服务器内部错误 |
| 503 | 服务降级（数据库/Redis 不可用） |
| 504 | 请求超时 |

---

## 认证方式

所有需认证的接口在请求头中携带 Token：

```
Authorization: Bearer <JWT_TOKEN>
```

### ⚠️ Token 获取方式

**Token 不在响应体中，仅在响应头 `Authorization` 中返回**，前端需从响应头提取：

```javascript
// 前端 axios 响应拦截器示例
const auth = res.headers['authorization']
const token = auth && auth.startsWith('Bearer ') ? auth.slice(7) : undefined
localStorage.setItem('token', token)
```

### Token 有效期

- 有效期默认 3600 分钟（可通过 `ACCESS_TOKEN_EXPIRE_MINUTES` 配置）
- 退出登录后 Token 加入黑名单立即失效
- 部分接口（微信小程序）也支持 `X-Token` 请求头
