# 数据库设计文档

## 概述

智能门禁管理系统使用 **MySQL 8.0** 作为主数据库，字符集为 `utf8mb4`（支持中文和 emoji），排序规则为 `utf8mb4_unicode_ci`。

数据库名称：`door_access_system`

## ER 关系图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    user     │       │ user_device │       │   device    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │──┐    │ id (PK)     │    ┌──│ id (PK)     │
│ username    │  │    │ user_id(FK) │────┘  │ name        │
│ password    │  │    │ device_id(FK│────┐  │ status      │
│ role        │  │    └─────────────┘    │  │ signal_str  │
│ phone       │  │                      │  │ location    │
│ email       │  │                      │  │ last_online │
│ openid      │  │                      │  │ created_at  │
│ avatar      │  │                      │  │ updated_at  │
│ created_at  │  │                      │  └──────┬──────┘
└──────┬──────┘  │                      │         │
       │         │                      │         │
       │         │    ┌─────────────────┼─────────┘
       │         │    │                 │
       │         │    │    ┌────────────┴──────┐
       │         │    │    │     door_log      │
       │         │    │    ├───────────────────┤
       │         └────┼───>│ id (PK)           │
       │              │    │ user_id (FK)      │
       │              │    │ device_id (FK)    │
       │              │    │ action            │
       │              │    │ status            │
       │              │    │ ip                │
       │              │    │ time              │
       │              │    └───────────────────┘
       │              │
       │    ┌─────────┴─────────┐       ┌─────────────────┐
       │    │   role            │       │  permission     │
       │    ├───────────────────┤       ├─────────────────┤
       └───>│ id (PK)           │──┐    │ id (PK)         │
            │ name              │  │    │ code            │
            │ code              │  │    │ name            │
            │ is_system         │  │    │ module          │
            │ created_at        │  │    │ sort            │
            └───────────────────┘  │    └────────┬────────┘
                                   │             │
                                   │    ┌────────┴────────┐
                                   │    │ role_permission │
                                   │    ├─────────────────┤
                                   └───>│ id (PK)         │
                                        │ role_id (FK)    │
                                        │ permission_id   │
                                        └─────────────────┘
```

## 表结构详解

### 1. user（用户表）

存储系统用户信息，支持普通登录和微信登录。

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | INT | PRIMARY KEY, INDEX | AUTO_INCREMENT | 用户唯一标识 |
| username | VARCHAR(50) | UNIQUE, INDEX, NOT NULL | - | 用户名（支持中文、下划线） |
| password | VARCHAR(100) | NOT NULL | - | bcrypt 哈希密码（72字节限制） |
| role | VARCHAR(20) | NOT NULL | "user" | 角色标识（admin/user/自定义） |
| phone | VARCHAR(20) | UNIQUE, INDEX, NULLABLE | NULL | 手机号（用于短信验证码登录） |
| email | VARCHAR(100) | UNIQUE, INDEX, NULLABLE | NULL | 邮箱（用于邮箱验证码登录） |
| openid | VARCHAR(100) | UNIQUE, INDEX, NULLABLE | NULL | 微信小程序 openid |
| avatar | VARCHAR(255) | NULLABLE | NULL | 头像 URL |
| created_at | DATETIME | NOT NULL | datetime.now | 注册时间 |

**索引说明：**
- `PRIMARY KEY (id)` — 主键索引
- `UNIQUE (username)` — 用户名唯一索引
- `UNIQUE (phone)` — 手机号唯一索引
- `UNIQUE (email)` — 邮箱唯一索引
- `UNIQUE (openid)` — 微信 openid 唯一索引

**业务规则：**
- 密码使用 bcrypt 哈希存储，最大 72 字节
- role 字段逻辑外键关联 role.code，但不强制约束（灵活性优先）
- phone、email、openid 均为可选字段，支持多种登录方式
- 用户删除时，关联的 user_device 记录级联删除，door_log 记录 user_id 置空

---

### 2. device（设备表）

存储门禁设备信息，对应实体硬件设备。

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | INT | PRIMARY KEY, INDEX | AUTO_INCREMENT | 设备唯一标识 |
| name | VARCHAR(100) | NOT NULL | - | 设备编号（如 "001"，对应 MQTT 主题） |
| status | VARCHAR(20) | NOT NULL | "offline" | 设备状态（online/offline） |
| signal_strength | INT | NULLABLE | NULL | WiFi 信号强度 RSSI (dBm) |
| location | VARCHAR(200) | NULLABLE | NULL | 设备安装位置描述 |
| last_online_at | DATETIME | NULLABLE | NULL | 最后在线时间 |
| created_at | DATETIME | NOT NULL | datetime.now | 创建时间 |
| updated_at | DATETIME | NOT NULL | datetime.now | 更新时间（自动更新） |

**索引说明：**
- `PRIMARY KEY (id)` — 主键索引

**业务规则：**
- name 字段对应 MQTT 主题中的 device_id（如 `door/001/command`）
- status 由 MQTT 心跳自动维护：收到 ONLINE 消息设为 online，Redis key 过期后自动设为 offline
- signal_strength 由 ESP32-S3 定时上报（RSSI 值）
- 设备删除前必须先解绑所有用户（user_device 记录）
- 设备删除时，关联的 door_log 记录 device_id 置空（保留日志）

---

### 3. user_device（用户设备关联表）

用户与设备的多对多关联表，控制用户可操作的设备范围。

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | INT | PRIMARY KEY, INDEX | AUTO_INCREMENT | 记录唯一标识 |
| user_id | INT | FOREIGN KEY → user.id, CASCADE | - | 用户 ID |
| device_id | INT | FOREIGN KEY → device.id, CASCADE, INDEX | - | 设备 ID |

**约束说明：**
- `UNIQUE (user_id, device_id)` — 用户-设备组合唯一
- `FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE` — 用户删除时级联删除
- `FOREIGN KEY (device_id) REFERENCES device(id) ON DELETE CASCADE` — 设备删除时级联删除

**业务规则：**
- 管理员无需绑定即可操作所有设备
- 普通用户只能操作已绑定的设备
- 绑定/解绑操作会清除该用户的设备列表缓存

---

### 4. door_log（开门日志表）

记录所有开门操作的详细日志。

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | INT | PRIMARY KEY, INDEX | AUTO_INCREMENT | 日志唯一标识 |
| user_id | INT | FOREIGN KEY → user.id, SET NULL | NULL | 操作用户 ID |
| device_id | INT | FOREIGN KEY → device.id, SET NULL | NULL | 设备 ID |
| action | VARCHAR(50) | NOT NULL | - | 操作类型（见下方说明） |
| status | VARCHAR(50) | NOT NULL | - | 操作结果（见下方说明） |
| ip | VARCHAR(50) | NULLABLE | NULL | 操作者 IP 地址 |
| time | DATETIME | NOT NULL | datetime.now | 操作时间 |

**索引说明：**
- `PRIMARY KEY (id)` — 主键索引
- `INDEX idx_door_log_user_time (user_id, time)` — 用户日志查询 + 时间排序
- `INDEX idx_door_log_device_id (device_id)` — 按设备查询
- `INDEX idx_door_log_time (time)` — 全局时间范围查询

**外键行为：**
- `FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL` — 用户删除时保留日志，user_id 置空
- `FOREIGN KEY (device_id) REFERENCES device(id) ON DELETE SET NULL` — 设备删除时保留日志，device_id 置空

**action 字段取值：**

| action 值 | 来源 | 说明 |
|-----------|------|------|
| 开门 | Web/小程序/APP | 远程开门（用户主动操作） |
| 密码开门 | STM32 本地 | 矩阵键盘输入密码 |
| 指纹开门 | STM32 本地 | AS608 指纹识别 |
| 刷卡开门 | STM32 本地 | MFRC522 RFID 刷卡 |

**status 字段取值：**

| status 值 | 说明 |
|-----------|------|
| 成功 | 开门成功 |
| 失败：无权限 | 用户无该设备权限 |
| 失败：设备离线 | 设备不在线 |
| 失败：xxx | 其他错误原因 |

**业务规则：**
- user_id 为 NULL：本地开门（密码/指纹/刷卡），无法关联具体用户
- ip 为 NULL：本地开门（STM32 直接操作）
- 日志只增不改不删，用于审计追溯
- 管理员可查看所有日志，普通用户只能查看自己的日志

---

### 5. role（角色表）

RBAC 权限系统的角色定义。

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | INT | PRIMARY KEY, INDEX | AUTO_INCREMENT | 角色唯一标识 |
| name | VARCHAR(30) | UNIQUE, NOT NULL | - | 角色名称（如"管理员"） |
| code | VARCHAR(30) | UNIQUE, INDEX, NOT NULL | - | 角色标识（如 admin） |
| is_system | BOOLEAN | NOT NULL | FALSE | 是否系统内置角色 |
| created_at | DATETIME | NOT NULL | datetime.now | 创建时间 |

**索引说明：**
- `PRIMARY KEY (id)` — 主键索引
- `UNIQUE (name)` — 角色名称唯一
- `UNIQUE (code)` — 角色标识唯一

**系统内置角色：**

| id | name | code | is_system | 说明 |
|----|------|------|-----------|------|
| 1 | 管理员 | admin | TRUE | 系统管理员，拥有所有权限 |
| 2 | 普通用户 | user | TRUE | 普通用户，基础权限 |

**业务规则：**
- is_system=TRUE 的角色不可删除
- user 表的 role 字段存储 role.code 而非 role.id（逻辑外键）
- 自定义角色可自由创建和删除

---

### 6. permission（权限表）

RBAC 权限系统的权限定义，按模块分组。

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | INT | PRIMARY KEY, INDEX | AUTO_INCREMENT | 权限唯一标识 |
| code | VARCHAR(50) | UNIQUE, INDEX, NOT NULL | - | 权限标识（如 user.manage） |
| name | VARCHAR(50) | NOT NULL | - | 权限名称（如"用户管理"） |
| module | VARCHAR(30) | NOT NULL | - | 所属模块（用于前端分组展示） |
| sort | INT | NOT NULL | 0 | 排序序号 |

**索引说明：**
- `PRIMARY KEY (id)` — 主键索引
- `UNIQUE (code)` — 权限标识唯一

**系统预设权限：**

| code | name | module | 说明 |
|------|------|--------|------|
| user.manage | 用户管理 | 用户 | 用户增删改查、角色分配 |
| device.manage | 设备管理 | 设备 | 设备增删改查、绑定解绑 |
| door.open | 远程开门 | 门禁 | 远程开启门禁 |
| door.log | 开门日志 | 门禁 | 查看全局开门日志 |

**业务规则：**
- 权限通过 role_permission 关联到角色
- 前端根据 permission.code 控制菜单和按钮显示
- 后端通过 `require_permission("code")` 装饰器校验接口权限

---

### 7. role_permission（角色权限关联表）

角色与权限的多对多关联表。

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | INT | PRIMARY KEY, INDEX | AUTO_INCREMENT | 记录唯一标识 |
| role_id | INT | FOREIGN KEY → role.id, CASCADE, NOT NULL | - | 角色 ID |
| permission_id | INT | FOREIGN KEY → permission.id, CASCADE, NOT NULL | - | 权限 ID |

**约束说明：**
- `UNIQUE (role_id, permission_id)` — 角色-权限组合唯一
- `FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE` — 角色删除时级联删除
- `FOREIGN KEY (permission_id) REFERENCES permission(id) ON DELETE CASCADE` — 权限删除时级联删除

**业务规则：**
- 管理员角色默认拥有所有权限
- 修改角色权限时整体替换（先删后增）
- 权限变更后，已登录用户的权限通过 Redis 缓存自动生效

---

## 数据库初始化

系统启动时（`main.py` lifespan）自动执行：

1. **建表**：`Base.metadata.create_all(bind=engine)` — 创建所有表（如不存在）
2. **创建管理员**：根据 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 环境变量创建默认管理员
3. **初始化权限**：
   - 创建默认角色（admin、user）
   - 创建默认权限（user.manage、device.manage、door.open、door.log）
   - 为管理员角色分配所有权限
4. **重置设备状态**：将所有设备标记为 offline（Redis 缓存重启后丢失）

## 数据库迁移

当前版本使用 SQLAlchemy 自动建表，不使用 Alembic 迁移工具。

**字段变更时的处理方式：**
- 新增字段：设置 `nullable=True` 或提供 `default` 值，确保兼容已有数据
- 删除字段：先确认无业务依赖，手动执行 `ALTER TABLE DROP COLUMN`
- 修改字段：谨慎评估影响，必要时手动执行 `ALTER TABLE MODIFY`

## 性能优化建议

### 索引策略
- door_log 表使用复合索引 `(user_id, time)` 覆盖用户日志查询
- door_log 表使用单列索引 `(time)` 覆盖管理员全局时间范围查询
- user 表对 username、phone、email、openid 建立唯一索引，同时加速查询

### 查询优化
- 用户列表查询：使用 `LIKE 'keyword%'` 前缀匹配，避免全表扫描
- 日志分页：使用 `LIMIT offset, size`，大偏移量时考虑基于游标的分页
- 统计数据：使用 Redis 缓存（180 秒 TTL），避免频繁 COUNT 查询

### 数据归档
- door_log 表会持续增长，建议定期归档历史数据
- 可按月分表或导出到数据仓库
- 保留最近 6 个月数据在主表，历史数据迁移到归档表

## 备份策略

```bash
# 备份数据库
mysqldump -u root -p door_access_system > backup_$(date +%Y%m%d).sql

# 恢复数据库
mysql -u root -p door_access_system < backup_20260607.sql

# Docker 环境备份
docker exec door-mysql mysqldump -u root -p door_access_system > backup.sql
```

## 字符集与排序规则

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 字符集 | utf8mb4 | 支持中文、emoji、特殊字符 |
| 排序规则 | utf8mb4_unicode_ci | Unicode 排序，不区分大小写 |
| 连接字符集 | utf8mb4 | SQLAlchemy 连接时自动设置 |
