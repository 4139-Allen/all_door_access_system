# 门禁日志接口测试文档

## 接口概览

| 端点 | 权限要求 | 角色等价类 |
|------|---------|-----------|
| `GET /door-logs` | `log.view` | admin(有) / 普通用户(无) / 停用用户(有但不可用) / 匿名(无token) |
| `GET /door/my-logs` | `door.view_own_log` | 普通用户(有) / admin(有) / 匿名(无token) |
| `GET /door-logs/export` | `log.export` | 同 `/door-logs` 授权矩阵 |

---

## 1. 输入参数等价类划分

### 1.1 page（整数，ge=1）

| 分区 | 代表值 | 预期 |
|------|--------|------|
| 无效：<1 | 0, -1 | 422 |
| 有效：≥1 | 1, 2, 9999 | 200 |

边界值：**0**(无效) → **1**(有效min) → **2**(内点)

### 1.2 size（整数，ge=1, le=100）

| 分区 | 代表值 | 预期 |
|------|--------|------|
| 无效：<1 | 0 | 422 |
| 有效：1~100 | 1, 10, 100 | 200 |
| 无效：>100 | 101 | 422 |

边界值：**0**(无效) → **1**(有效min) → **100**(有效max) → **101**(无效)

### 1.3 username / device_name（模糊搜索，含 LIKE 特殊字符）

| 分区 | 代表值 | 预期 |
|------|--------|------|
| 不传/空字符串 | 不传 | 不过滤 |
| 存在（完全匹配） | `username=admin` | 命中 |
| 存在（部分匹配） | `username=ad` | 命中 |
| 不存在 | `username=__虚拟用户__` | total=0 |
| 含 LIKE 特殊字符 | `username=admin_`, `device_name=100%` | 精确字面匹配，不按通配符展开 |

测试策略：username/device_name 相同结构，选 **username 做全覆盖**，device_name 做抽样验证即可。

### 1.4 status（前缀匹配）

| 分区 | 代表值 | 预期 |
|------|--------|------|
| 不传/空字符串 | 不传 | 不过滤 |
| 有匹配（前缀命中） | `status=成功` | 匹配"成功"、"成功：远程开门" |
| 无匹配 | `status=__虚拟状态__` | total=0 |
| 特殊字符 | `status=失败%` | 转义处理 |

### 1.5 start_time / end_time（日期范围）

| 分区 | 代表值 | 预期 |
|------|--------|------|
| 无效：start>end | `start=2026-12-31&end=2026-01-01` | 422 |
| 无效：非日期格式 | `start=abc` | 422 |
| 有效：不传 | 不传 | 不过滤 |
| 有效：仅 start | `start=2026-01-01` | time ≥ start |
| 有效：仅 end | `end=2026-12-31` | time ≤ end |
| 有效：start≤end | `start=2026-01-01&end=2026-12-31` | 范围内 |

---

## 2. 测试用例

### 2.1 授权矩阵（等价类：角色 × 端点）

角色 × 端点交叉，共 **12 条**：

| ID | 角色 | 端点 | 预期 code |
|----|------|------|-----------|
| A01 | admin | `GET /door-logs` | 200 |
| A02 | 普通用户 | `GET /door-logs` | 403 |
| A03 | 匿名 | `GET /door-logs` | 401 |
| A04 | 停用用户 | `GET /door-logs` | 401 |
| A05 | 普通用户 | `GET /door/my-logs` | 200 |
| A06 | admin | `GET /door/my-logs` | 200 |
| A07 | 匿名 | `GET /door/my-logs` | 401 |
| A08 | admin | `GET /door-logs/export` | 200 |
| A09 | 普通用户 | `GET /door-logs/export` | 403 |
| A10 | 匿名 | `GET /door-logs/export` | 401 |
| A11 | 普通用户 | `GET /door-logs?username=xxx` | 403（无 log.view 不能调此接口） |
| A12 | 普通用户传 username | `GET /door/my-logs?username=admin` | 200（忽略 username，查自己） |

### 2.2 分页（边界值）

| ID | 参数 | 断言 |
|----|------|------|
| P01 | 默认（不传） | 200，`len(list) ≤ 10`，total ≥ 0 |
| P02 | `page=1&size=5` | `len(list) ≤ 5` |
| P03 | `page=1&size=1` | `len(list) ≤ 1` |
| P04 | `page=1&size=100` | `len(list) ≤ 100` |
| P05 | `page=1&size=101` | 422 |
| P06 | `page=1&size=0` | 422 |
| P07 | `page=0` | 422 |
| P08 | `page=9999` | list 为空，total 正确 |
| P09 | page=1 + page=2（`size=5`） | 两页 id 无重叠 |

### 2.3 筛选条件

条件间相互独立（AND 关系），每个条件用等价类覆盖即可，无需全排列。

#### 2.3.1 username（仅管理员 `/door-logs`）

| ID | 参数 | 断言 |
|----|------|------|
| F01 | `username=admin`（完全匹配） | 全部结果 username 包含"admin" |
| F02 | `username=ad`（模糊匹配） | 全部结果 username 包含"ad" |
| F03 | `username=__不存在__` | total=0 |
| F04 | `username=admin%`（特殊字符转义） | `%` 不做通配符，精确匹配 |
| F05 | `username=_`（特殊字符转义） | `_` 不做单字符通配，精确匹配 |

#### 2.3.2 device_name（抽样，与 username 同逻辑）

| ID | 参数 | 断言 |
|----|------|------|
| F06 | `device_name=大门`（存在） | 结果全部含"大门" |
| F07 | `device_name=__不存在__` | total=0 |
| F08 | `device_name=DEV_01`（特殊字符转义） | `_` 精确匹配 |

#### 2.3.3 status

| ID | 参数 | 断言 |
|----|------|------|
| F09 | `status=成功` | 全部 status 以"成功"开头 |
| F10 | `status=失败` | 全部 status 以"失败"开头（含"失败：无权限"等） |
| F11 | `status=__不存在__` | total=0 |

#### 2.3.4 时间范围

| ID | 参数 | 断言 |
|----|------|------|
| F12 | `start_time=2026-01-01&end_time=2026-12-31` | 范围内 |
| F13 | `start_time=2026-06-01`（仅开始） | time ≥ 2026-06-01 |
| F14 | `end_time=2026-06-01`（仅结束） | time ≤ 2026-06-01 |
| F15 | `start_time=2026-12-31&end_time=2026-01-01`（倒置） | 422 |
| F16 | `start_time=abc`（非法格式） | 422 |

### 2.4 组合筛选

条件间 AND 运算，选一个代表性组合验证即可：

| ID | 参数 | 断言 |
|----|------|------|
| C01 | `device_name=大门&status=成功&start_time=2026-01-01&end_time=2026-12-31` | 全部条件同时生效 |

### 2.5 数据隔离

| ID | 场景 | 操作 | 断言 |
|----|------|------|------|
| I01 | 用户只能看自己日志 | userA 调 `/door/my-logs` | 全部 result.user_id = userA.id |
| I02 | 无日志用户 | 新注册用户调 `/door/my-logs` | list 为空，total=0 |

### 2.6 数据容错（数据层状态）

| ID | 场景 | 数据前提 | 断言 |
|----|------|---------|------|
| D01 | 设备已删除 | DoorLog.device_id 对应的 Device 记录已删除 | `device_name="未知设备"` |
| D02 | 用户已删除 | DoorLog.user_id 对应的 User 记录已删除 | `username="未知用户"` |
| D03 | 本地开门（无用户） | DoorLog.user_id = NULL | `username="本地"` |

### 2.7 响应结构

| ID | 断言 |
|----|------|
| R01 | data 包含 list/total/page/size |
| R02 | list 中每条记录包含 id, user_id, username, device_id, device_name, device_location, action, status, ip, time |
| R03 | msg 随筛选条件变化（`_build_admin_log_msg` / `_build_my_log_msg`） |

---

## 3. 测试数据要求

- 至少 2 个用户（admin + 普通用户），至少 1 个停用账号
- 至少 15 条日志，覆盖：
  - 不同用户（含 NULL，即本地开门）
  - 不同设备
  - 不同状态（成功/失败等）
  - 不同时间（含跨月/跨年）
  - 至少 1 条日志关联的设备已被删除
  - 至少 1 条日志关联的用户已被删除

---

## 4. 汇总

| 模块 | 用例数 |
|------|--------|
| 授权矩阵 | 12 |
| 分页边界值 | 9 |
| 筛选条件 | 16 |
| 组合筛选 | 1 |
| 数据隔离 | 2 |
| 数据容错 | 3 |
| 响应结构 | 3 |
| **合计** | **46** |
