# API 文档

> **基准地址**: `http://127.0.0.1:8000/api`（开发） / `https://www.doorlink.top/api`（生产）
>
> **交互式文档**: `http://127.0.0.1:8000/docs`（Swagger UI）/ `http://127.0.0.1:8000/redoc`（ReDoc）

---

## 目录

- [统一响应格式](#统一响应格式)
- [通用错误码](#通用错误码)
- [认证方式](#认证方式)
- [认证管理](#认证管理)
- [微信小程序认证](#微信小程序认证)
- [用户管理](#用户管理)
- [设备管理](#设备管理)
- [门禁管理](#门禁管理)
- [异常事件](#异常事件)
- [权限管理](#权限管理)
- [数据统计](#数据统计)
- [AI 智能助手](#ai-智能助手)
- [WebSocket 协议](#websocket-协议)
- [系统健康检查](#系统健康检查)

---

## 统一响应格式

所有 API 响应统一格式：

### 成功响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": { ... }
}
```

### 错误响应

```json
{
  "code": 400,
  "msg": "具体错误信息",
  "data": null
}
```

### 翻页列表格式

所有翻页列表统一返回 `{total, page, size, list}`：

```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "total": 100,
    "page": 1,
    "size": 10,
    "list": [ ... ]
  }
}
```

---

## 通用错误码

| HTTP 状态码 | code | msg | 说明 |
|------------|------|-----|------|
| 200 | 200 | 操作成功 | 请求成功 |
| 400 | 400 | 具体错误信息 | 业务逻辑错误（如用户名已存在、密码错误） |
| 401 | 401 | 未提供认证凭证 / Token 无效或已过期 | 未登录或 Token 失效 |
| 403 | 403 | 无操作权限 | 当前用户无此接口的权限 |
| 404 | 404 | 资源不存在 | 请求的资源（用户/设备等）不存在 |
| 422 | 422 | 字段名+具体错误 | 请求参数校验失败（如密码太短） |
| 429 | 429 | 请求过于频繁，请 N 秒后再试 | 登录接口频率限制（5次/60秒） |
| 500 | 500 | 服务器内部错误，请联系超级管理员 | 未预料的服务器异常 |

---

## 认证方式

所有需要认证的接口在请求头中携带 Token：

```
Authorization: Bearer <token>
```

另外支持通过 `X-Token` 请求头传递（用于微信小程序等无法自定义 Authorization 的场景）。

### 获取 Token

**Token 不在响应体中，仅在响应头 `Authorization` 中返回**，前端需从响应头提取：

```javascript
const auth = res.headers['authorization']
const token = auth && auth.startsWith('Bearer ') ? auth.slice(7) : undefined
```

### Token 有效期

- 有效期默认 3600 分钟（可通过 `ACCESS_TOKEN_EXPIRE_MINUTES` 配置）
- 退出登录后 Token 加入黑名单立即失效

---

## 认证管理

| 方法 | 路径 | 描述 | 权限 | 限流 |
|------|------|------|------|------|
| POST | `/auth/login` | 统一密码登录（手机号/邮箱/用户名） | 公开 | 5 次/60s |
| POST | `/auth/login-code` | 统一验证码登录（手机号/邮箱） | 公开 | 5 次/60s |
| POST | `/auth/send-code` | 发送验证码（手机号或邮箱） | 公开 | 5 次/60s |
| POST | `/auth/register` | 用户注册（创建普通用户） | 公开 | 5 次/60s |
| POST | `/auth/logout` | 退出登录（Token 加入黑名单） | 已认证 | - |
| PUT | `/auth/password` | 修改当前用户密码 | 已认证 | - |
| POST | `/auth/reset-password` | 忘记密码（手机号+验证码重置） | 公开 | 5 次/60s |
| GET | `/auth/profile` | 获取个人信息（含手机号/邮箱） | 已认证 | - |
| GET | `/auth/permissions` | 刷新当前用户的权限列表 | 已认证 | - |
| PUT | `/auth/profile` | 修改用户名 | 已认证 | - |
| PUT | `/auth/avatar` | 上传头像 | 已认证 | - |
| PUT | `/auth/bind-phone` | 绑定手机号（需验证码） | 已认证 | - |
| PUT | `/auth/bind-email` | 绑定邮箱（需验证码） | 已认证 | - |
| DELETE | `/auth/bind-phone` | 解绑手机号 | 已认证 | - |
| DELETE | `/auth/bind-email` | 解绑邮箱 | 已认证 | - |

### POST /auth/login — 统一密码登录

> `username` 支持手机号、邮箱或用户名，后端自动识别。

```json
{
  "username": "admin",
  "password": "123456"
}
```

响应（Token 在响应头 `Authorization` 中）:

```json
{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "user_id": 1,
    "role": "admin",
    "role_name": "超级管理员",
    "username": "admin",
    "avatar": "/uploads/avatars/xxx.jpg",
    "permissions": ["dashboard.view", "door.open", "device.view", ...]
  }
}
```

### POST /auth/login-code — 统一验证码登录

> 自动识别手机号或邮箱，未注册的凭据自动创建账号（用户名即为手机号/邮箱，无密码）。用户名不支持验证码登录。

```json
{
  "username": "13800138000",
  "code": "123456"
}
```

```json
{"code": 200, "msg": "登录成功", "data": {同上}}
```

### POST /auth/register — 用户注册

**字段校验**:

| 字段 | 规则 |
|------|------|
| username | 1-32 字符，支持中文、字母、数字、下划线、点、中划线 |
| password | 6-20 字符 |

```json
{
  "username": "newuser",
  "password": "123456"
}
```

```json
// 响应 201
{"code": 200, "msg": "用户注册成功", "data": {"id": 2, "username": "newuser", "role": "user"}}
```

### POST /auth/send-code — 发送验证码

```json
{
  "target": "13800138000"
}
```

> `target` 支持手机号（11 位）或邮箱。手机号发短信，邮箱发邮件。

```json
{"code": 200, "msg": "验证码已发送", "data": null}
```

### POST /auth/logout — 退出登录

**请求头**: `Authorization: Bearer <token>`

```json
{"code": 200, "msg": "退出成功，Token 已失效", "data": null}
```

### PUT /auth/password — 修改密码

```json
{"old_password": "123456", "new_password": "newpass123"}
```

> 未设置密码的用户（手机号注册）`old_password` 传 `null`。

```json
{"code": 200, "msg": "密码修改成功", "data": null}
```

### POST /auth/reset-password — 忘记密码

```json
{"phone": "13800138000", "code": "123456", "new_password": "newpass123"}
```

```json
{"code": 200, "msg": "密码重置成功", "data": null}
```

### GET /auth/profile — 获取个人信息

```json
{
  "code": 200,
  "msg": "获取个人信息成功",
  "data": {
    "id": 1,
    "username": "admin",
    "phone": "13800138000",
    "email": "admin@example.com",
    "role": "admin",
    "role_name": "超级管理员",
    "avatar": "/uploads/avatars/xxx.jpg",
    "has_password": true,
    "created_at": "2026-01-01 00:00:00"
  }
}
```

### GET /auth/permissions — 刷新当前用户的权限列表

> 清除缓存并重新查询当前用户的权限，用于管理员修改权限后前端主动刷新。

```json
{"code": 200, "msg": "权限刷新成功", "data": {"permissions": ["dashboard.view", "door.open", "device.view", ...]}}
```

### PUT /auth/profile — 修改用户名

```json
{"username": "new_name"}
```

```json
{"code": 200, "msg": "用户名修改成功", "data": null}
```

### PUT /auth/avatar — 上传头像

`multipart/form-data`，字段名 `file`

| 限制项 | 说明 |
|--------|------|
| 文件格式 | JPG、PNG、GIF、WebP |
| 文件大小 | ≤ 1MB |

```json
{"code": 200, "msg": "头像上传成功", "data": {"avatar": "/uploads/avatars/1_abc123.jpg"}}
```

### PUT /auth/bind-phone — 绑定手机号

> 需先获取验证码。同一手机号只能绑定一个账号。

```json
{"phone": "13800138000", "code": "123456"}
```

```json
{"code": 200, "msg": "手机号绑定成功", "data": null}
```

### PUT /auth/bind-email — 绑定邮箱

```json
{"email": "user@example.com", "code": "123456"}
```

```json
{"code": 200, "msg": "邮箱绑定成功", "data": null}
```

### DELETE /auth/bind-phone / DELETE /auth/bind-email — 解绑

```json
{"code": 200, "msg": "手机号解绑成功", "data": null}
```

---

## 微信小程序认证

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/auth/wx-login` | 微信小程序登录（code → JWT） | 公开 |
| PUT | `/auth/wx-bind` | 绑定已有账号到微信 | 已认证（微信 Token） |

### POST /auth/wx-login — 微信小程序登录

```json
{"code": "wx_login_code"}
```

> `code` 通过微信 `wx.login()` 获取。新用户自动注册。Token 在响应头中返回。

### PUT /auth/wx-bind — 绑定已有账号

```json
{"username": "admin", "password": "123456"}
```

---

## 用户管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/users` | 用户列表（分页+筛选） | `user.view` |
| POST | `/users` | 创建用户 | `user.manage` |
| PUT | `/users/{user_id}/role` | 修改用户角色 | `user.manage` |
| DELETE | `/users/{user_id}` | 删除用户 | `user.manage` |
| POST | `/users/import` | 批量导入用户（Excel） | `user.manage` |
| GET | `/users/{user_id}/devices` | 查询用户绑定的设备 | `user.view` |

### GET /users — 获取用户列表

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| size | int | 10 | 每页条数（最大 100） |
| username | str | - | 用户名模糊搜索（最长 50 字符） |
| role | str | - | 角色筛选：`admin` / `operator` / `user` |
| show_inactive | bool | false | 是否显示已停用用户 |

```json
{
  "code": 200,
  "msg": "获取用户列表成功",
  "data": {
    "total": 50,
    "page": 1,
    "size": 10,
    "list": [
      {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "role_name": "超级管理员",
        "avatar": "",
        "is_builtin": true,
        "devices": [
          {"name": "001", "location": "正门"},
          {"name": "002", "location": "侧门"}
        ],
        "created_at": "2026-01-01 00:00:00"
      }
    ]
  }
}
```

> `devices` 为用户已绑定的设备列表（名称+位置），空数组表示未绑定设备。`is_builtin` 为 `true` 表示内置账号（如超级管理员），不可删除。

### POST /users — 创建用户

```json
{"username": "newuser", "password": "123456", "role": "user"}
```

**校验**: `role` 必须是已存在的角色（系统角色 `admin`/`operator`/`user` 或自定义角色），否则返回 400 `角色 'x' 不存在`。

```json
// 响应 201
{"code": 200, "msg": "用户创建成功", "data": {"id": 3, "username": "newuser", "role": "user"}}
```

### PUT /users/{user_id}/role — 修改角色

**限制**: 不能修改自己的角色、超级管理员（`admin`）角色不可修改。

```json
{"role": "operator"}
```

```json
{"code": 200, "msg": "角色修改成功", "data": {"user_id": 2, "username": "user1", "role": "operator", "role_name": "普通管理员"}}
```

### DELETE /users/{user_id} — 删除用户

> 删除为**软删除（停用）**：自动解绑该用户所有设备，并释放用户名/手机号/邮箱。

**限制**: 不能删除自己、不能删除系统内置账号（如超级管理员）、已停用的用户不可重复删除。

```json
{"code": 200, "msg": "停用成功", "data": null}
```

### POST /users/import — 批量导入用户

`multipart/form-data`，字段名 `file`

- 仅支持 `.xlsx` / `.xls`
- Excel 第一列=用户名，第二列=密码（可选，默认 `123456`）
- 从第 2 行开始读（第 1 行为表头）

```json
{
  "code": 200,
  "msg": "成功导入 10 个用户，2 个失败",
  "data": {
    "success_count": 10,
    "fail_count": 2,
    "fail_list": ["第5行：用户名已存在", "第8行：密码长度不能少于6个字符"],
    "msg": "成功导入 10 个用户，2 个失败"
  }
}
```

### GET /users/{user_id}/devices — 查询绑定的设备

> 返回完整设备对象（用于绑定管理页双栏展示）。用户不存在时返回 404 `用户不存在`（已停用用户仍存在，返回空数组）。

```json
{
  "code": 200,
  "msg": "获取用户设备成功",
  "data": [
    {
      "id": 1,
      "name": "001",
      "location": "正门",
      "status": "online",
      "signal_strength": -65,
      "last_online_at": "2026-07-19 10:30:00"
    }
  ]
}
```

---

## 设备管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/devices` | 设备列表（分页+名称筛选） | `device.view` 或 `door.open` |
| POST | `/devices` | 新增设备 | `device.create` |
| PUT | `/devices/{device_id}` | 更新设备信息 | `device.edit` |
| DELETE | `/devices/{device_id}` | 删除设备 | `device.delete` |
| POST | `/devices/{device_id}/bind` | 绑定用户到设备 | `device.bind` |
| DELETE | `/devices/{device_id}/unbind` | 解绑用户与设备 | `device.bind` |

### GET /devices — 获取设备列表

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| size | int | 10 | 每页条数（最大 100） |
| name | str | - | 设备名称模糊搜索（最长 100 字符） |

> 有 `device.view` 权限可查看全部设备，否则只能查看已绑定的设备。

```json
{
  "code": 200,
  "msg": "获取设备列表成功",
  "data": {
    "total": 10,
    "page": 1,
    "size": 10,
    "list": [
      {
        "id": 1,
        "name": "001",
        "location": "正门",
        "status": "online",
        "signal_strength": -65,
        "last_online_at": "2026-07-19 10:30:00"
      }
    ]
  }
}
```

> `status`：`online`（在线）/ `offline`（离线）。在线状态由 Redis 实时叠加，比数据库状态更准确。

### POST /devices — 新增设备

设备名唯一、不可重复；设备名与位置均为必填。

```json
{"name": "001", "location": "正门"}
```

```json
// 响应 201
{"code": 200, "msg": "创建设备成功", "data": {"device_id": 1}}
```

### PUT /devices/{device_id} — 更新设备

```json
{"name": "新名称", "location": "新位置", "status": "online"}
```

```json
{"code": 200, "msg": "更新成功", "data": null}
```

### DELETE /devices/{device_id} — 删除设备

**限制**: 已绑定用户的设备需先解绑才能删除。

```json
{"code": 200, "msg": "删除成功", "data": null}
```

### POST /devices/{device_id}/bind — 绑定用户

```json
{"user_id": 1}
```

```json
{"code": 200, "msg": "绑定成功", "data": null}
```

### DELETE /devices/{device_id}/unbind — 解绑用户

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | int | 是 | 用户ID |

```json
{"code": 200, "msg": "解绑成功", "data": null}
```

---

## 门禁管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/doors/{device_id}/open` | 远程开门 | `door.open` |
| GET | `/door-logs` | 开门日志（分页+筛选，管理员看全部） | `log.view` |
| GET | `/door/my-logs` | 个人开门日志（分页+筛选） | `door.view_own_log` |
| GET | `/door-logs/export` | 导出门禁日志（Excel） | `log.export` |

### POST /doors/{device_id}/open — 远程开门

> 后台通过 MQTT 发送开门命令到硬件，异步等待设备回复确认。

```json
{
  "code": 200,
  "msg": "已成功开启：001（正门）",
  "data": {
    "device_id": 1,
    "device_name": "001",
    "location": "正门",
    "username": "admin",
    "time": "2026-07-19 10:00:00",
    "success": true
  }
}
```

### GET /door-logs — 获取开门日志（管理员查看全部）

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| size | int | 10 | 每页数量（最大 100） |
| username | str | - | 用户名模糊搜索 |
| device_name | str | - | 设备名称模糊搜索 |
| status | str | - | 状态筛选（支持前缀匹配，如"失败"匹配"失败：无权限"） |
| start_time | datetime | - | 开始时间 |
| end_time | datetime | - | 结束时间 |

> 需 `log.view` 权限。普通用户请使用 `GET /door/my-logs` 查看自己的日志。

```json
{
  "code": 200,
  "msg": "获取日志成功，共 200 条",
  "data": {
    "total": 200,
    "page": 1,
    "size": 10,
    "list": [
      {
        "id": 1,
        "username": "admin",
        "device_name": "001",
        "device_location": "正门",
        "action": "远程开门",
        "status": "成功",
        "ip": "192.168.1.100",
        "time": "2026-07-19 10:00:00"
      }
    ]
  }
}
```

> 日志表采用反规范化存储（用户名/设备名直接冗余在日志行），因此响应不含 `user_id` / `device_id` 字段。

### GET /door/my-logs — 获取个人开门日志（普通用户）

参数与 `/door-logs` 一致（`username` 筛选仅管理员可用），但只返回当前用户的日志，需 `door.view_own_log` 权限。

### GET /door-logs/export — 导出门禁日志（Excel）

筛选参数与 `/door-logs` 一致（无 `page`/`size`），需 `log.export` 权限。

> 默认最多导出 `LOG_EXPORT_MAX_ROWS`（默认 10000）条；超限时仅导出最新记录，并在响应中标记 `truncated`。

```json
{
  "code": 200,
  "msg": "导出 10000 条记录（超过上限，仅导出最新 10000 条，请缩小筛选范围）",
  "data": {
    "list": [ ... 与 /door-logs 单条结构相同 ... ],
    "truncated": true,
    "max_rows": 10000
  }
}
```

**status 常见值**:

| 值 | 说明 |
|----|------|
| 成功 | 开门成功 |
| 失败：密码错误 | 密码验证失败 |
| 失败：指纹不匹配 | 指纹验证失败 |
| 失败：未授权卡片 | 刷卡验证失败 |
| 失败：设备已锁定（剩余N秒） | 设备因错误次数过多被锁定 |

---

## 异常事件

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/alerts` | 异常事件列表（分页+筛选） | `alert.view` |
| GET | `/alerts/stats` | 异常事件统计 | `alert.view` |
| POST | `/alerts/unlock/{device_name}` | 解除设备锁定 | `alert.unlock` |

### GET /alerts — 获取异常事件列表

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| size | int | 10 | 每页数量（最大 100） |
| device_name | str | - | 设备名称筛选 |
| alert_type | str | - | 事件类型：`lock` / `offline` / `error` |
| start_time | str | - | 开始时间 |
| end_time | str | - | 结束时间 |

**事件类型**:

| type | 级别 | 说明 |
|------|------|------|
| lock | danger | 设备锁定（连续 5 次错误） |
| error | warning | 开门失败 |
| offline | warning | 设备离线 |

```json
{
  "code": 200,
  "msg": "获取异常事件列表成功，共 10 条",
  "data": {
    "total": 10,
    "page": 1,
    "size": 10,
    "list": [
      {
        "id": 1,
        "username": "本地",
        "device_name": "001",
        "device_location": "正门",
        "action": "密码开门",
        "status": "失败：验证错误次数过多，设备锁定5分钟",
        "event_type": "lock",
        "event_level": "danger",
        "ip": "",
        "time": "2026-07-19 09:30:00"
      }
    ]
  }
}
```

### GET /alerts/stats — 获取异常事件统计

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| hours | int | 24 | 统计时间范围（小时），1-720 |

```json
{
  "code": 200,
  "msg": "获取异常事件统计成功",
  "data": {
    "total_alerts": 15,
    "lock_count": 3,
    "error_count": 12,
    "device_stats": [
      {"name": "001", "count": 8},
      {"name": "002", "count": 7}
    ],
    "locked_devices": [
      {"device_id": 1, "device_name": "001", "device_location": "正门", "lock_ttl": 180}
    ],
    "time_range_hours": 24
  }
}
```

### POST /alerts/unlock/{device_name} — 解除设备锁定

> 清除 Redis 锁定键 + 发送 MQTT UNLOCK 命令给硬件设备。

```json
{"code": 200, "msg": "设备 001 锁定已解除", "data": null}
```

### 设备自动锁定规则

| 方式 | 触发 | 条件 | 锁定时长 |
|------|------|------|----------|
| 密码 | PWD_ERR | 连续 5 次错误 | 5 分钟 |
| 指纹 | FP_ERR | 连续 5 次错误 | 5 分钟 |
| 刷卡 | CARD_ERR | 连续 5 次错误 | 5 分钟 |

---

## 权限管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/permissions` | 获取所有权限（按模块分组） | `user.manage` |
| GET | `/roles` | 获取所有角色及权限 | `user.manage` |
| POST | `/roles` | 创建自定义角色 | `user.manage` |
| PUT | `/roles/{role_id}` | 修改角色名称 | `user.manage` |
| DELETE | `/roles/{role_id}` | 删除角色 | `user.manage` |
| PUT | `/roles/{role_id}/permissions` | 设置角色权限（全量替换） | `user.manage` |

### GET /permissions — 权限列表

```json
{
  "code": 200,
  "msg": "获取权限列表成功",
  "data": [
    {
      "module": "仪表盘",
      "permissions": [{"id": 1, "code": "dashboard.view", "name": "查看仪表盘"}]
    },
    {
      "module": "门禁控制",
      "permissions": [
        {"id": 2, "code": "door.open", "name": "远程开门"},
        {"id": 3, "code": "door.view_own_log", "name": "查看自己的开门记录"}
      ]
    },
    {
      "module": "设备管理",
      "permissions": [
        {"id": 4, "code": "device.view", "name": "查看设备列表"},
        {"id": 5, "code": "device.create", "name": "创建设备"},
        {"id": 6, "code": "device.edit", "name": "编辑设备"},
        {"id": 7, "code": "device.delete", "name": "删除设备"},
        {"id": 8, "code": "device.bind", "name": "绑定/解绑用户"}
      ]
    },
    {
      "module": "日志管理",
      "permissions": [
        {"id": 9, "code": "log.view", "name": "查看门禁日志"},
        {"id": 10, "code": "log.export", "name": "导出日志"}
      ]
    },
    {
      "module": "异常事件",
      "permissions": [
        {"id": 11, "code": "alert.view", "name": "查看异常事件"},
        {"id": 12, "code": "alert.unlock", "name": "解除设备锁定"}
      ]
    },
    {
      "module": "用户管理",
      "permissions": [
        {"id": 13, "code": "user.view", "name": "查看用户列表"},
        {"id": 14, "code": "user.manage", "name": "管理用户"}
      ]
    }
  ]
}
```

### POST /roles — 创建角色

```json
{"name": "安保员", "code": "security"}
```

```json
{"code": 200, "msg": "创建成功", "data": {"id": 5, "name": "安保员", "code": "security"}}
```

### PUT /roles/{role_id}/permissions — 设置角色权限

> 超级管理员角色的权限不可修改。全量替换（传入的 `permission_ids` 会覆盖原有权限）。

```json
{"permission_ids": [1, 2, 3, 4, 5]}
```

```json
{"code": 200, "msg": "权限设置成功", "data": {"role_id": 2, "role_name": "普通管理员", "permission_count": 5}}
```

---

## 数据统计

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/statistics` | 获取统计数据（角色区分） | `dashboard.view` |
| GET | `/statistics/trend` | 本周开锁趋势（按天统计） | `dashboard.view` |
| GET | `/statistics/actions` | 开锁方式占比分布 | `dashboard.view` |

### GET /statistics — 统计数据

> **管理员**：全系统统计。**普通用户**：个人统计。缓存 180 秒。

```json
{
  "code": 200,
  "msg": "获取统计数据成功",
  "data": {
    "user_total": 50,
    "device_online": 8,
    "device_offline": 2,
    "today_log": 120
  }
}
```

### GET /statistics/trend — 本周趋势

```json
{
  "code": 200,
  "msg": "获取趋势数据成功",
  "data": [
    {"day": "07/13", "count": 15},
    {"day": "07/14", "count": 22},
    {"day": "07/15", "count": 18},
    {"day": "07/16", "count": 30},
    {"day": "07/17", "count": 25},
    {"day": "07/18", "count": 20},
    {"day": "07/19", "count": 12}
  ]
}
```

### GET /statistics/actions — 开锁方式占比

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| days | int | 7 | 统计最近 N 天，`0` = 全部时间 |

```json
{
  "code": 200,
  "msg": "获取开锁方式数据成功",
  "data": [
    {"name": "远程", "value": 80},
    {"name": "密码", "value": 30},
    {"name": "指纹", "value": 15},
    {"name": "RFID", "value": 5}
  ]
}
```

---

## AI 智能助手

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/ai/chat` | AI 智能开门/查询（自然语言） | `door.open` + `device.view` |

### POST /ai/chat — AI 指令

**支持的指令**:

| 类型 | 示例 |
|------|------|
| 开门 | "打开 001"、"开启教学楼的门" |
| 查询日志 | "今天开了多少次门"、"查看今天的开门记录" |
| 设备状态 | "有哪些设备"、"设备运行状态怎么样" |
| 用户统计 | "系统有多少用户" |
| 对话 | "你好"、"谢谢" |

```json
{"message": "打开正门"}
```

```json
{"code": 200, "msg": "操作成功", "data": {"reply": "已成功开启：001（正门）"}}
```

> 需配置 `DEEPSEEK_API_KEY` 环境变量。对话上下文 Redis 缓存 15 分钟。

---

## WebSocket 协议

**端点**: `ws://127.0.0.1:8000/api/ws`

### 认证流程

1. 客户端发起 WebSocket 连接
2. 客户端 10 秒内发送认证消息：

```json
{"type": "auth", "token": "your_jwt_token"}
```

3. 服务端返回：

```json
// 成功
{"type": "auth", "status": "ok"}
// 失败
{"type": "auth", "status": "failed", "msg": "Token 无效"}
```

### 服务端推送消息

**开门事件**（有 `log.view` 权限或绑定了该设备的用户收到）:

```json
{
  "type": "door_open",
  "message": "【admin】远程开启了【001】(正门)",
  "username": "admin",
  "device_name": "001",
  "location": "正门",
  "action": "远程开门",
  "status": "成功",
  "timestamp": "2026-07-19 10:00:00",
  "device_id": 1
}
```

**设备状态变更**（有 `device.view` 权限的用户收到）:

```json
{
  "type": "device_status",
  "device_id": 1,
  "device_name": "001",
  "status": "online",
  "location": "正门"
}
```

**异常告警**（有 `alert.view` 权限的用户收到）:

```json
{
  "type": "alert",
  "alert_type": "lock",
  "device_id": 1,
  "device_name": "001",
  "message": "验证错误次数过多，设备已锁定5分钟",
  "timestamp": "2026-07-19 09:30:00"
}
```

---

## 系统健康检查

### GET /api/health — 健康检查

**权限**: 公开

> 用于 Docker 容器健康检查，检测 MySQL 和 Redis 连通性。`healthy` 时 HTTP 200，`degraded` 时 HTTP 503。

```json
// 正常
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "status": "healthy",
    "service": "door_access_system",
    "checks": {
      "database": "ok",
      "redis": "ok"
    }
  }
}

// 降级（HTTP 503）
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "status": "degraded",
    "service": "door_access_system",
    "checks": {
      "database": "ok",
      "redis": "error: no connection"
    }
  }
}
```
