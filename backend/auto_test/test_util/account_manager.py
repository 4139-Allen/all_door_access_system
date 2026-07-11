"""
测试账号管理器

职责：
  1. 从 test_env.yaml 读取各环境账号配置
  2. 支持环境变量注入（密码不落盘）
  3. 自动登录并缓存 token（会话级复用）
  4. 提供不同角色的已登录 ApiClient

用法：
    mgr = AccountManager("dev")
    admin_client = mgr.get_client("admin")      # 自动登录，返回已认证的 ApiClient
    user_client  = mgr.get_client("regular_user")
    anon_client  = ApiClient(mgr.base_url)       # 未登录
"""
import os
import logging
import re
from pathlib import Path
from typing import Dict, Optional

import yaml

from test_util.http_client import ApiClient

logger = logging.getLogger("auto_test")


class AccountManager:
    """账号管理器：加载配置、自动登录、缓存 token"""

    def __init__(self, env: str = "dev"):
        self.env = env
        self._config = self._load_config()
        self.base_url = self._config["base_url"]
        self._token_cache: Dict[str, str] = {}

    # ---------- 配置加载 ----------

    def _load_config(self) -> dict:
        """加载 test_env.yaml，支持环境变量注入"""
        config_path = (
            Path(__file__).parent.parent / "config" / "test_env.yaml"
        )
        if not config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {config_path}\n"
                f"请从 test_env.yaml.example 复制并填写真实信息"
            )

        with open(config_path, encoding="utf-8") as f:
            raw = f.read()

        # 替换 ${VAR_NAME} 为环境变量
        def _replace_env_var(match):
            var_name = match.group(1)
            value = os.getenv(var_name)
            if value is None:
                logger.warning(f"⚠️  环境变量 {var_name} 未设置，将使用原始占位符")
                return match.group(0)
            return value

        resolved = re.sub(r"\$\{(\w+)\}", _replace_env_var, raw)
        config = yaml.safe_load(resolved)

        env_config = config.get(self.env)
        if not env_config:
            raise ValueError(
                f"未找到环境 '{self.env}' 的配置，可用环境: "
                f"{[k for k in config.keys() if not k.startswith('_') and k != 'default_env']}"
            )
        return env_config

    # ---------- 客户端获取 ----------

    def get_client(self, role: str = "admin") -> ApiClient:
        """
        获取指定角色的已登录 ApiClient

        参数：
            role: 角色标识（admin / regular_user / unbound_user / readonly）

        返回：
            已注入 Authorization header 的 ApiClient
        """
        if role not in self._token_cache:
            self._login(role)
        return ApiClient(self.base_url, token=self._token_cache[role])

    def get_client_no_auth(self) -> ApiClient:
        """获取未登录的 ApiClient（测试未认证场景）"""
        return ApiClient(self.base_url)

    # ---------- 内部：自动登录 ----------

    def _login(self, role: str):
        """登录指定角色账号并缓存 token"""
        account = self._get_account(role)
        if not account:
            raise ValueError(
                f"环境 '{self.env}' 未配置角色 '{role}' 的账号信息"
            )

        client = ApiClient(self.base_url)
        resp = client.post(
            "/auth/login",
            json={
                "username": account["username"],
                "password": account["password"],
            },
        )
        body = resp.json()

        if resp.status_code != 200 or body.get("code") != 200:
            raise RuntimeError(
                f"账号登录失败 [env={self.env}, role={role}]: "
                f"{resp.status_code} {body.get('msg', '')}"
            )

        # token 在响应头 Authorization 中，不在 body
        auth_header = resp.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "")
        if not token:
            raise RuntimeError(
                f"登录成功但未获取到 token [env={self.env}, role={role}]\n"
                f"响应头: {dict(resp.headers)}"
            )
        self._token_cache[role] = token
        logger.info(
            f"✅ 账号登录成功 [env={self.env}, role={role}, "
            f"user={account['username']}]"
        )

    def _get_account(self, role: str) -> Optional[dict]:
        """获取账号配置"""
        return self._config.get(role)

    # ---------- 数据库配置（可选） ----------

    @property
    def db_config(self) -> Optional[dict]:
        """获取数据库连接配置（用于 db_util 数据校验）"""
        return self._config.get("database")
