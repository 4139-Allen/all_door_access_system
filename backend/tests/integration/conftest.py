"""
写一个新模块的测试，顺序永远是：

  ① 写 fixture  ─→  ② 写测试用例  ─→  ③ 写 assert
     ↑ 最难          ↑ 中间            ↑ 最简单

集成测试共享 fixture（固定装置）
========================
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

# 使用内存 SQLite 数据库进行测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话（每个函数独立，自动建表/清理）"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # 清理所有表数据
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端（依赖注入已替换为测试数据库会话）"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """创建测试普通用户"""
    user = User(
        username="testuser",
        password=hash_password("testpass123"),
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session):
    """创建测试管理员用户"""
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
    """创建测试设备"""
    device = Device(
        name="001",
        location="校门",
        status="online"
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


@pytest.fixture
def auth_headers(client, test_user):
    """获取普通用户的认证头"""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    token = response.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, test_admin):
    """获取管理员的认证头"""
    response = client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "adminpass123"
    })
    token = response.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def fresh_manager():
    """提供干净的 ConnectionManager 实例用于测试"""
    from services.websocket_service import ConnectionManager
    return ConnectionManager()


@pytest.fixture(scope="function", autouse=True)
def clean_redis_before_test():
    """每次测试前清空 Redis，保证完全隔离"""
    try:
        if redis_client:
            redis_client.flushdb()
    except Exception:
        pass
    yield
