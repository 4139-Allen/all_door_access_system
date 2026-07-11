"""
统一 HTTP 请求封装

职责：
  1. 封装 requests 库，自动拼接 base_url
  2. 自动注入 Authorization header
  3. 统一的超时、重试、日志记录
  4. 响应自动 JSON 解析 + 错误抛出

用法：
    client = ApiClient("http://127.0.0.1:8000/api", token="xxx")
    resp = client.post("/auth/login", json={...})
    # resp 是 requests.Response 对象，可直接 .json()
"""
import logging
import time
from typing import Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("auto_test")


class ApiClient:
    """统一 HTTP 客户端"""

    def __init__(
        self,
        base_url: str,
        token: str = None,
        timeout: int = 15,
        max_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # 带重试机制的 session
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 默认请求头
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DoorAccessAutoTest/1.0",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    # ---------- 核心请求方法 ----------

    def request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> requests.Response:
        """
        发送 HTTP 请求

        参数：
            method: GET / POST / PUT / DELETE
            path:   API 路径（如 /auth/login），会自动拼接 base_url
            **kwargs: 传给 requests.Session.request 的参数（json, params, headers 等）

        返回：
            requests.Response 对象
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)

        # 记录请求日志
        logger.debug(f"➡️  {method} {path}")

        start = time.time()
        resp = self.session.request(method, url, **kwargs)
        elapsed = round(time.time() - start, 3)

        logger.debug(
            f"⬅️  {method} {path} → {resp.status_code} ({elapsed}s)"
        )
        return resp

    # ---------- 便捷方法 ----------

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)

    # ---------- 会话管理 ----------

    def set_token(self, token: str):
        """设置/更新认证 token"""
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_token(self):
        """清除认证 token（模拟未登录）"""
        self.session.headers.pop("Authorization", None)

    def close(self):
        self.session.close()
