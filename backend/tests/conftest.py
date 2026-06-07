"""
Pytest 全局配置和 fixtures
提供数据库会话、测试客户端等共享资源
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database.db import Base, get_db
from database.redis import redis_client
from database.models.user import User
from database.models.device import Device
from database.models.door_log import DoorLog
from database.models.user_device import UserDevice
from utils.auth import hash_password
from main import app
import os

# 测试环境下禁用频率限制
os.environ["DISABLE_RATE_LIMITER"] = "true"

# 使用内存 SQLite 数据库进行测试
# 内存数据库，不生成文件（最干净）
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# 文件数据库
# SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ====================== 测试结束删除 test.db ======================
@pytest.fixture(scope="session", autouse=True)
def auto_clean_test_files():
    """
    测试会话结束后自动清理 test.db 垃圾文件
    不管成功失败，最后都会清理
    """
    yield  # 等待所有测试跑完

    # 测试结束后删除文件数据库（如果存在）
    test_db_file = "./test.db"
    if os.path.exists(test_db_file):
        os.remove(test_db_file)
        print("\n✅ 测试完成，已自动清理 test.db")


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
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
    """创建测试客户端"""

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