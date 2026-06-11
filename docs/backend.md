# 后端详细说明

## 项目结构

```
backend/
├── main.py                       # 应用入口（lifespan、CORS、中间件）
├── serial_mqtt_bridge.py         # STM32 串口-MQTT 桥接脚本
├── requirements.txt              # Python 依赖
├── Dockerfile.backend            # Docker 构建文件
├── .env.example                  # 环境变量模板
├── .env.docker                   # Docker 环境变量模板
├── api/                          # API 层（路由定义）
│   ├── routers.py                # 路由聚合器
│   ├── auth_api.py               # 认证接口（登录/注册/退出/改密）
│   ├── wx_auth_api.py            # 微信小程序认证
│   ├── admin_user_api.py         # 用户管理（管理员）
│   ├── device_api.py             # 设备管理
│   ├── door_api.py               # 门禁控制 + 开门日志
│   ├── alert_api.py              # 异常事件（设备锁定/开门失败）
│   ├── permission_api.py         # 权限管理（角色/权限 CRUD）
│   ├── stat_api.py               # 数据统计
│   ├── ai_agent.py               # AI 助手接口
│   └── websocket_api.py          # WebSocket 实时通知
├── services/                     # 服务层（业务逻辑）
│   ├── admin_user_service.py     # 用户业务
│   ├── device_service.py         # 设备业务（含 Redis 缓存）
│   ├── device_monitor_service.py # 设备在线状态监控（后台定时巡检）
│   ├── door_service.py           # 门禁业务 + 日志查询
│   ├── mqtt_service.py           # MQTT 通信管理
│   ├── alert_service.py          # 异常事件业务（设备锁定/解锁/统计）
│   ├── websocket_service.py      # WebSocket 连接管理 + 认证
│   ├── permission_service.py     # RBAC 权限业务
│   ├── stat_service.py           # 统计业务
│   ├── ai_agent_service.py       # AI 助手业务（DeepSeek）
│   ├── verify_code_service.py    # 短信/邮箱验证码服务
│   └── wx_auth_service.py        # 微信登录业务
├── database/                     # 数据层
│   ├── db.py                     # SQLAlchemy 引擎 + 初始化
│   ├── redis.py                  # Redis 连接管理（单例 + 自动重连）
│   └── models/                   # ORM 模型
│       ├── user.py               # 用户表
│       ├── device.py             # 设备表
│       ├── door_log.py           # 开门日志表
│       ├── user_device.py        # 用户-设备绑定表
│       ├── role.py               # 角色表
│       ├── permission.py         # 权限表
│       └── role_permission.py    # 角色-权限关联表
├── core/                         # 核心配置
│   ├── config.py                 # 环境变量加载
│   ├── exceptions.py             # 自定义异常
│   ├── response_schema.py        # 统一响应格式定义（ApiResponse）
│   └── ai_system_prompt.py       # AI 系统提示词
├── utils/                        # 工具层
│   ├── auth.py                   # JWT 认证 + 密码哈希 + 权限校验装饰器
│   ├── logger.py                 # 日志管理（30天轮转）
│   ├── rate_limiter.py           # 请求频率限制（Redis 滑动窗口）
│   ├── api_exception_handler.py  # API 异常处理装饰器
│   └── service_exception_handler.py # 服务层异常装饰器（自动回滚）
├── schemas/                      # Pydantic 校验
│   ├── user_schema.py
│   ├── device_schema.py
│   ├── door_schema.py
│   └── permission_schema.py
├── tests/                        # 测试用例（9 个模块）
│   ├── conftest.py               # 测试 fixtures
│   ├── test_auth.py              # 认证测试
│   ├── test_user.py              # 用户管理测试
│   ├── test_device.py            # 设备管理测试
│   ├── test_door.py              # 门禁控制测试
│   ├── test_stat.py              # 统计测试
│   ├── test_ai_agent.py          # AI 助手测试
│   ├── test_schema.py            # Schema 校验测试
│   └── test_api.py               # 通用 API 测试
└── logs/                         # 运行日志（app.log + 30天轮转）
```

## 三层架构

```
API 层 (api/)            接收请求、参数校验、调用服务层、返回统一响应
    ↓
服务层 (services/)       业务逻辑、数据库查询、MQTT 通信、缓存管理、权限校验
    ↓
数据层 (database/)       SQLAlchemy ORM、Redis 缓存、数据库初始化
```

**关键设计模式：**
- **装饰器统一异常处理**：`@handle_api_exception`（HTTP）和 `@handle_websocket_exception`（WebSocket）自动捕获异常并返回标准格式
- **服务层异常装饰器**：`@service_exception_handler` 自动回滚数据库事务
- **单例模式**：Redis 客户端、MQTT 管理器、WebSocket 连接管理器、日志器均为单例
- **Redis 优雅降级**：Redis 不可用时系统正常运行，仅缓存和令牌管理受影响
- **FastAPI 依赖注入**：`get_db`（数据库会话）、`get_current_user_obj`（当前用户）、`require_admin`（管理员校验）、`require_permission("code")`（细粒度权限校验）

## 数据库模型

### user（用户表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| username | String(50) UNIQUE | 用户名（支持中文、下划线） |
| password | String(100) | bcrypt 哈希密码（72 字节限制） |
| role | String(20) | 角色标识：admin / user（或自定义角色 code） |
| openid | String(100) UNIQUE | 微信 openid（可空） |
| created_at | DateTime | 创建时间 |

### device（设备表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| name | String(100) | 设备编号（如 "001"，对应 MQTT 主题中的 device_id） |
| status | String(20) | 状态：online / offline |
| location | String(200) | 位置描述 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间（自动） |

### user_device（用户设备关联表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| user_id | Integer FK → user.id | CASCADE 删除 |
| device_id | Integer FK → device.id | CASCADE 删除，索引 |

### door_log（开门日志表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| user_id | Integer FK → user.id | SET NULL 删除（保留日志） |
| device_id | Integer FK → device.id | SET NULL 删除（保留日志） |
| action | String(50) | 动作：开门 / 密码开门 / 指纹开门 / 刷卡开门 |
| status | String(50) | 结果：成功 / 失败：xxx |
| time | DateTime | 时间（自动） |

索引：`(user_id, time)` 复合索引、`device_id` 索引、`time` 索引

### role（角色表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| name | String(30) UNIQUE | 角色名称（如"管理员"、"普通用户"） |
| code | String(30) UNIQUE | 角色标识（如 admin、user），索引 |
| is_system | Boolean | 是否系统内置角色（不可删除） |
| created_at | DateTime | 创建时间 |

### permission（权限表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| code | String(50) UNIQUE | 权限标识（如 user.manage、device.manage），索引 |
| name | String(50) | 权限名称（如"用户管理"、"设备管理"） |
| module | String(30) | 所属模块（如"用户"、"设备"、"门禁"） |
| sort | Integer | 排序序号 |

### role_permission（角色权限关联表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| role_id | Integer FK → role.id | CASCADE 删除 |
| permission_id | Integer FK → permission.id | CASCADE 删除 |

约束：`(role_id, permission_id)` 唯一约束

### RBAC 权限系统

系统启动时自动初始化：
1. 创建默认角色：`admin`（管理员）、`user`（普通用户）
2. 创建默认权限：`user.manage`、`device.manage`、`door.open`、`door.log` 等
3. 为管理员角色分配所有权限

权限校验流程：
```
请求 → require_permission("code") → 查询用户角色 → 查询角色权限 → 允许/拒绝
```

## Redis 缓存策略

| 缓存键 | 过期时间 | 用途 |
|--------|----------|------|
| `token:{token}` | 同 Token 有效期 | 活跃会话令牌 |
| `blacklist:{token}` | 86400s (24h) | 注销令牌黑名单 |
| `cache:device:list:user:{id}` | 60s | 用户设备列表 |
| `stat:user:{id}` | 180s | 统计数据 |
| `ai:context:user:{id}` | 900s (15min) | AI 对话上下文 |
| `device:online:{mqtt_name}` | 70s | 设备在线状态（MQTT 心跳） |
| `door:err:fail:{device_name}` | 300s (5min) | 验证错误计数（密码/指纹/刷卡） |
| `door:err:lock:{device_name}` | 300s (5min) | 设备锁定状态 |
| `cache:alerts:*` | 30s | 异常事件列表缓存 |
| `verify_code:{target}` | 300s (5min) | 短信/邮箱验证码 |
| `verify_rate:{target}` | 60s | 验证码发送频率限制 |

### 缓存失效规则
- 设备 CRUD 操作 → 清除所有用户的 `cache:device:list:user:*`
- 设备绑定/解绑 → 清除对应用户的 `cache:device:list:user:{id}`
- 统计缓存 → 仅 TTL 过期，不做主动失效
- AI 对话 → 成功开门后清除 `ai:context:user:{id}`
- 设备在线状态 → MQTT 心跳刷新 TTL，过期自动标记离线

## MQTT 通信

### 主题规范
| 主题 | 方向 | 说明 |
|------|------|------|
| `door/{device_name}/command` | 服务器 → 设备 | 开门指令（`OPEN_DOOR`） |
| `door/{device_name}/status` | 设备 → 服务器 | 状态上报 |

### 状态上报格式
| 消息 | 含义 |
|------|------|
| `ONLINE` | 设备上线 |
| `OK` / `OPENED` | 远程开门成功 |
| `PWD_OK` | 密码开门成功 |
| `FP_OK` | 指纹开门成功 |
| `CARD_OK` | 刷卡开门成功 |
| `PWD_ERR` | 密码验证错误 |
| `FP_ERR` | 指纹验证错误 |
| `CARD_ERR` | 刷卡验证错误 |
| `LOCK` | 设备锁定触发 |

### 后端处理流程
1. 接收 `ONLINE` → 更新 Redis `device:online:{name}`（70s TTL）+ 同步数据库状态为 online + WebSocket 通知管理员设备上线
2. 接收 `PWD_OK`/`FP_OK`/`CARD_OK` → 写入 DoorLog（user_id=None）+ WebSocket 通知管理员
3. 发送 `OPEN_DOOR` → QoS 1 发布到设备命令主题
4. 设备状态监控服务每 25 秒巡检一次，Redis key 过期 → 自动标记离线 + WebSocket 通知

## 设备在线状态监控

`device_monitor_service.py` 实现后台异步监控：

1. **标记在线**：MQTT 收到 `ONLINE` 消息时调用 `mark_device_online()`
2. **定时巡检**：每 25 秒检查已知在线设备的 Redis key 是否存在
3. **自动离线**：Redis key 过期 → 更新数据库状态为 offline → WebSocket 推送离线通知
4. **生命周期**：随 FastAPI lifespan 启停

## 验证码服务

`verify_code_service.py` 提供短信和邮箱验证码功能：

- **短信验证码**：阿里云短信 API（SendSmsVerifyCode / CheckSmsVerifyCode）
- **邮箱验证码**：SMTP 发送 HTML 格式验证码邮件（支持 SSL/STARTTLS）
- **频率限制**：Redis 控制，60 秒内同一目标只能发送一次
- **有效期**：5 分钟（Redis TTL）
- **自动识别**：根据目标格式自动判断手机号或邮箱

## 异常事件服务

`alert_service.py` 处理设备锁定和安全告警相关业务：

### 设备自动锁定机制

当 STM32 设备连续验证错误 5 次（密码/指纹/刷卡），后端自动锁定设备：

1. **错误计数**：MQTT 收到 `PWD_ERR`/`FP_ERR`/`CARD_ERR` → Redis `door:err:fail:{device_name}` 计数 +1（TTL 300s）
2. **触发锁定**：计数达到 5 → 设置 `door:err:lock:{device_name}`（TTL 300s）→ 发送 `LOCK` 命令给 STM32
3. **成功重置**：收到 `PWD_OK`/`FP_OK`/`CARD_OK` → 删除错误计数键
4. **自动解锁**：锁定键 TTL 过期（5 分钟）后自动解锁

### 异常事件查询

- **列表查询**：从 DoorLog 表筛选 `status` 包含"失败"或"锁定"的记录
- **统计查询**：按时间范围统计异常总数、锁定次数、失败次数、各设备分布
- **锁定列表**：扫描 Redis `door:err:lock:*` 键获取当前锁定设备及剩余 TTL
- **缓存策略**：查询结果缓存 30 秒，新增异常事件时自动清除所有缓存

### 手动解除锁定

管理员可通过 API 手动解除设备锁定：
1. 删除 Redis `door:err:lock:{device_name}` 和 `door:err:fail:{device_name}`
2. 通过 MQTT 发送 `UNLOCK` 命令给 STM32
3. 记录操作日志

## 异常处理

API 层和 WebSocket 层各有统一的异常处理装饰器，自动捕获：

| 异常类型 | HTTP 状态码 | 说明 |
|----------|------------|------|
| `ValueError` | 400 | 业务逻辑错误 |
| `PermissionError` | 403 | 权限不足 |
| `NotFoundError` | 404 | 资源不存在 |
| `AuthError` | 401 | 认证失败 |
| `TooManyRequestsError` | 429 | 请求频率过高 |
| `TimeoutError` | 504 | 请求超时 |
| `Exception` | 500 | 服务器内部错误 |

### 统一响应格式

所有 API 响应遵循 `{"code": int, "msg": str, "data": any}` 格式：

```json
// 成功
{"code": 200, "msg": "操作成功", "data": {...}}

// 失败
{"code": 400, "msg": "错误信息", "data": null}
```
