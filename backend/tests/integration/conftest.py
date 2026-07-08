"""
集成测试共享 fixture（固定装置）
=================================
作用范围：tests/integration/ 下所有测试

提供：
  - 内存 SQLite 数据库引擎与会话
  - FastAPI TestClient
  - 测试用户/设备数据
  - 认证头
  - Redis 清理
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database.db import Base, get_db
from database.redis import redis_client
from database.models.user import User
from database.models.device import Device
from utils.auth import hash_password
from main import app


# ===================== 第 1 步：创建测试数据库引擎 =====================

# 生产环境用 MySQL，测试用 SQLite 内存数据库。
# 优势：① 安装即用（Python 自带）② 快（纯内存读写）
#       ③ 隔离（每次测试从零开始）④ 干净（结束自动消失）
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# create_engine 是 SQLAlchemy 的数据库引擎，
# 可以理解为「数据库连接工厂」，需要连接时找它要。
#
# 参数解释：
#   check_same_thread=False
#     默认 SQLite 只允许创建它的线程使用。测试时 pytest 可能切换线程，
#     关闭这个限制让任何线程都能用。
#
#   poolclass=StaticPool
#     SQLite 内存模式不支持多连接（因为数据库在内存里只有一份），
#     StaticPool 让所有请求共用同一个内存连接。
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# sessionmaker 是「会话工厂」——调用它得到一个数据库会话。
# 会话 = 用来执行 SQL 的中间人。
# bind=engine：告诉它用上面那个引擎来创建连接。
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ===================== 第 2 步：定义 fixture =====================

# ———— 2a. 数据库会话 ————

@pytest.fixture(scope="function")
def db_session():
    """
    提供测试数据库会话。

    scope="function" 表示每个测试函数独立使用。
    测试开始前建表，结束后删表，互不干扰。

    执行流程：
      1. create_all → 在内存中创建 User、Device 等所有表
      2. yield db   → 把会话交给测试函数
      3. drop_all   → 测试跑完，清空所有表
    """
    # 建表：在内存 SQLite 中创建所有模型对应的表
    # Base 是所有模型的父类，create_all 扫描所有继承 Base 的模型
    Base.metadata.create_all(bind=engine)

    # 创建数据库会话（相当于打开一个数据库连接）
    db = TestingSessionLocal()
    try:
        yield db  # ← 测试函数在这里运行，db 就是它们用的数据库
    finally:
        db.close()
        # 删表：清空所有数据，下一个测试从零开始
        Base.metadata.drop_all(bind=engine)


# ———— 2b. HTTP 测试客户端 ————

@pytest.fixture(scope="function")
def client(db_session):
    """
    提供模拟 HTTP 客户端。

    TestClient 是 FastAPI 自带的测试工具。
    它不启动真实服务器（不走端口），而是直接调用 FastAPI 内部的路由逻辑。

    关键操作：dependency_overrides
      FastAPI 的 Depends(get_db) 在测试时被替换，
      让所有接口的数据库请求都指向测试的 db_session（SQLite），
      而不是生产环境的 get_db（MySQL）。
    """

    # 定义一个「假的 get_db」——不再连 MySQL，而是返回测试会话
    def override_get_db():
        try:
            yield db_session  # 返回内存 SQLite 的会话
        finally:
            pass

    # 替换 FastAPI 的依赖表：
    #   Depends(get_db) → 本应调用 get_db()
    #   现在改为调用 override_get_db()
    #   所以整个应用在测试期间用的都是内存 SQLite
    app.dependency_overrides[get_db] = override_get_db

    # 创建测试客户端（不启动真实服务器）
    with TestClient(app) as test_client:
        yield test_client  # ← 测试函数用它来发 HTTP 请求

    # 测试结束后，恢复原来的依赖表，避免影响其他测试
    app.dependency_overrides.clear()


# ———— 2c. 测试数据：用户和设备 ————

@pytest.fixture
def test_user(db_session):
    """
    在数据库中创建一条普通用户记录。

    字段说明：
      username = "testuser"     — 登录时用的用户名
      password = hash_password  — bcrypt 哈希后的密码（不是明文！）
      role = "user"             — 普通用户（非管理员）

    db_session.refresh(user) 从数据库重新读取刚插入的数据，
    这样返回的 user 对象才有完整的 id 等字段。
    """
    user = User(
        username="testuser",
        password=hash_password("testpass123"),
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user  # 把这个用户对象交给测试函数用


@pytest.fixture
def test_admin(db_session):
    """
    在数据库中创建一条管理员用户记录。

    与 test_user 的唯一区别：role="admin"
    """
    admin = User(
        username="testadmin",
        password=hash_password("adminpass123"),
        role="admin"
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def test_device(db_session):
    """
    在数据库中创建一台测试设备。

    设备字段：
      name = "001"     — 设备编号
      location = "校门" — 安装位置
      status = "online" — 初始状态在线
    """
    device = Device(
        name="001",
        location="校门",
        status="online"
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


# ———— 2d. 认证头 ————

@pytest.fixture
def auth_headers(client, test_user):
    """
    通过真实的登录 API 获取普通用户的 JWT Token。

    流程：
      1. 用 testuser / testpass123 调用登录接口
      2. 从返回的 JSON 中提取 token
      3. 构造 Authorization 头

    返回的 headers 可以直接传给需要认证的 API 测试。
    注意：这里的登录请求同样走 TestClient，用的是内存 SQLite。
    """
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    return {"Authorization": response.headers["authorization"]}


@pytest.fixture
def admin_headers(client, test_admin):
    """
    获取管理员用户的 JWT Token。

    与 auth_headers 逻辑相同，只是登录的是管理员账号。
    """
    response = client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "adminpass123"
    })
    return {"Authorization": response.headers["authorization"]}


# ———— 2e. WebSocket 连接管理器（很少用到） ————

@pytest.fixture
def fresh_manager():
    """
    创建一个全新的 WebSocket ConnectionManager 实例。
    用于测试 WebSocket 推送逻辑。
    """
    from services.websocket_service import ConnectionManager
    return ConnectionManager()


# ———— 2f. 自动清理 Redis ————

@pytest.fixture(scope="function", autouse=True)
def clean_redis_before_test():
    """
    每次测试前自动清空 Redis。

    autouse=True：所有测试自动使用，不需要手动声明。
    Redis 不可用时（未安装/未启动），会自动跳过，不影响测试结果。
    """
    try:
        if redis_client:
            redis_client.flushdb()
    except Exception:
        pass
    yield
