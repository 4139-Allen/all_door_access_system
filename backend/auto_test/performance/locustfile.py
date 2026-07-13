"""
门禁系统性能测试脚本 (Locust)

模拟多种用户行为对系统进行压力测试，找出性能瓶颈。

## 使用方式

### 1. 安装 Locust
pip install locust

### 2. 启动 Web 界面（推荐）
cd backend/auto_test
locust -f performance/locustfile.py

打开 http://localhost:8089
设置总用户数 + 每秒启动数 → 开始压测

### 3. 命令行模式（无界面）
locust -f performance/locustfile.py --headless -u 50 -r 5 --run-time 60s

参数说明:
  -u 50      模拟 50 个并发用户
  -r 5       每秒启动 5 个用户
  --run-time 60s  持续压 60 秒

### 4. 生成报告
locust -f performance/locustfile.py --headless -u 50 -r 5 --run-time 60s \
  --html reports/perf_report.html --csv reports/perf_data

## 测试场景

| 用户类型 | 行为 | 权重 |
|---------|------|------|
| 管理员   | 查看统计、设备列表、日志 | 30% |
| 普通用户 | 查看设备、查日志 | 60% |
| 登录    | 登录认证 | 10% |

"""
import os
import time
import random
import uuid
from locust import HttpUser, task, between, constant


HOST = os.getenv("PERF_HOST", "http://127.0.0.1:8000/api")


class AdminUser(HttpUser):
    """模拟管理员行为：查看统计、设备、日志"""

    host = HOST
    wait_time = between(0.5, 3)  # 每次操作间隔 0.5~3 秒

    def on_start(self):
        """每个模拟用户启动时登录一次"""
        resp = self.client.post("/auth/login", json={
            "username": "admin",
            "password": "123456",
        })
        if resp.status_code == 200:
            body = resp.json()
            if body.get("code") == 200:
                token = resp.headers.get("Authorization", "").replace("Bearer ", "")
                self.client.headers.update({"Authorization": f"Bearer {token}"})
        else:
            self.stop(True)

    @task(3)
    def view_statistics(self):
        """查看仪表盘统计"""
        with self.client.get("/statistics", name="GET /statistics", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"状态码: {resp.status_code}")

    @task(2)
    def view_devices(self):
        """查看设备列表"""
        page = random.randint(1, 5)
        with self.client.get(f"/devices?page={page}&size=10", name="GET /devices", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"状态码: {resp.status_code}")

    @task(2)
    def view_logs(self):
        """查看开门日志"""
        with self.client.get("/door-logs?page=1&size=20", name="GET /door-logs", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"状态码: {resp.status_code}")

    @task(1)
    def view_users(self):
        """查看用户列表"""
        with self.client.get("/users?page=1&size=10", name="GET /users", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"状态码: {resp.status_code}")


class RegularUser(HttpUser):
    """模拟普通用户行为：看设备、查日志"""

    host = HOST
    wait_time = between(1, 5)

    def on_start(self):
        """注册并登录一个普通用户"""
        name = f"perf_user_{uuid.uuid4().hex[:12]}"
        self.client.post("/auth/register", json={
            "username": name,
            "password": "test123456",
        })
        resp = self.client.post("/auth/login", json={
            "username": name,
            "password": "test123456",
        })
        if resp.status_code == 200 and resp.json().get("code") == 200:
            token = resp.headers.get("Authorization", "").replace("Bearer ", "")
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(4)
    def view_my_devices(self):
        """查看自己的设备列表"""
        with self.client.get("/devices?page=1&size=10", name="GET /devices (user)", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"状态码: {resp.status_code}")

    @task(3)
    def view_my_logs(self):
        """查看自己的开门日志"""
        with self.client.get("/door-logs?page=1&size=10", name="GET /door-logs (user)", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"状态码: {resp.status_code}")

    @task(1)
    def get_profile(self):
        """查看个人信息"""
        with self.client.get("/auth/profile", name="GET /auth/profile", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"状态码: {resp.status_code}")


class LoginOnly(HttpUser):
    """模拟频繁登录场景（token 过期后重新登录）"""

    host = HOST
    wait_time = constant(3)

    @task
    def login(self):
        """登录 -> 登出"""
        with self.client.post("/auth/login", json={
            "username": "admin",
            "password": "123456",
        }, name="POST /auth/login", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"登录失败: {resp.status_code}")
