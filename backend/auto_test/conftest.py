"""
pytest 全局 Fixture

职责：
  1. 解析 --env 命令行参数（选择测试环境）
  2. 提供 AccountManager 单例（全局复用）
  3. 提供 admin_client / user_client / anon_client 等已认证客户端
  4. 可选：提供 DBUtil 数据库校验工具
  5. 自动记录测试执行日志

用法：
    def test_login(admin_client):
        resp = admin_client.post("/auth/login", json={...})
"""
import logging
import uuid
from pathlib import Path

import pytest

from test_util.account_manager import AccountManager
from test_util.http_client import ApiClient
from test_util.db_util import DBUtil

# ---------- 日志配置 ----------
_log_format = (
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logging.basicConfig(
    level=logging.INFO,
    format=_log_format,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("auto_test")


# ==================== 命令行参数 ====================


def pytest_addoption(parser):
    """注册自定义命令行参数"""
    parser.addoption(
        "--env",
        default="dev",
        help="测试环境: dev / staging / production",
    )
    parser.addoption(
        "--db-check",
        action="store_true",
        default=False,
        help="启用数据库校验（需配置 database 连接信息）",
    )


# ==================== Session 级别 Fixture ====================


@pytest.fixture(scope="session")
def env(request) -> str:
    """当前测试环境名称"""
    return request.config.getoption("--env")


@pytest.fixture(scope="session")
def account_manager(env: str) -> AccountManager:
    """AccountManager 单例（全局复用，减少重复登录）"""
    mgr = AccountManager(env)
    logger.info(f"🔧 测试环境: {env} | 服务地址: {mgr.base_url}")
    return mgr


# ==================== 已认证客户端 Fixture ====================


@pytest.fixture(scope="session")
def admin_client(account_manager: AccountManager) -> ApiClient:
    """
    管理员客户端（session 级复用）

    所有需要管理员权限的测试用例使用此 fixture。
    token 在整个 session 中只登录一次，避免重复请求。
    """
    return account_manager.get_client("admin")


@pytest.fixture
def user_client(account_manager: AccountManager) -> ApiClient:
    """
    普通用户客户端（function scope，每个测试独立创建）

    每个测试用例注册一个独立用户，互不干扰。
    登出、改密码、删用户等操作不会影响其他测试。

    无需 config 预配置账号。
    """
    client = account_manager.get_client_no_auth()
    name = f"auto_test_user_{uuid.uuid4().hex[:8]}"

    # 注册（注册接口返回 201 Created）
    resp = client.post("/auth/register", json={
        "username": name,
        "password": "test123456",
    })
    if resp.status_code not in (200, 201):
        name = f"auto_test_user_{uuid.uuid4().hex[:8]}"
        resp = client.post("/auth/register", json={
            "username": name,
            "password": "test123456",
        })
        assert resp.status_code in (200, 201), f"用户注册失败: {resp.text}"

    # 登录
    resp = client.post("/auth/login", json={
        "username": name,
        "password": "test123456",
    })
    body = resp.json()
    assert body.get("code") == 200, f"用户登录失败: {resp.text}"

    # token 在响应头 Authorization 中，不在 body
    auth_header = resp.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    client.set_token(token)
    logger.info(f"✅ 普通用户创建并登录成功: {name}")
    return client


# ==================== 每次测试独立的 Fixture ====================


@pytest.fixture
def anon_client(account_manager: AccountManager) -> ApiClient:
    """
    未登录客户端（每次测试新实例）

    用于测试未认证场景，避免请求头污染。
    """
    return account_manager.get_client_no_auth()


# ==================== 可选：数据库校验 ====================


@pytest.fixture(scope="session")
def db_util(account_manager: AccountManager, request) -> DBUtil:
    """
    数据库校验工具（可选，需要 --db-check 参数）

    启用手动时，可在测试中通过 db_util 直连数据库验证数据持久化结果。
    用法：
        def test_create_user(admin_client, db_util):
            ...
            db_util.assert_user_exists("new_user")
    """
    if not request.config.getoption("--db-check"):
        return None

    db_cfg = account_manager.db_config
    if not db_cfg:
        logger.warning("⚠️  test_env.yaml 中未配置 database 信息，跳过数据库校验")
        return None

    db = DBUtil(env_config=db_cfg)
    db.connect()
    yield db
    db.close()

# ==================== 钩子：测试结果记录 ====================


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """在测试失败时打印更多上下文"""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        logger.error(f"❌ 测试失败: {item.nodeid}")
        # 如果有响应体信息，打印出来
        if hasattr(item, "_last_response"):
            logger.error(f"   最后响应: {item._last_response[:500]}")
