"""
全局测试配置
==================================
作用范围：tests/ 下所有测试（unit/ + integration/）

职责（只放全局共用的内容）：
1. 将 backend/ 加入 sys.path，让测试文件能 import 项目模块
2. 设置测试环境变量（如禁用限流）
3. 定义 session 级别的自动清理 fixture

注意：数据库引擎、测试客户端、测试数据等 fixture 放在各自子目录的 conftest.py 中，
不需要被 unit/ 测试看见的 fixture 不要放在这里。
"""
import sys
from pathlib import Path

# 将 backend/ 目录加入 Python 模块搜索路径
sys.path.append(str(Path(__file__).parent.parent))

import os

# 测试环境下禁用频率限制（所有测试共享）
os.environ["DISABLE_RATE_LIMITER"] = "true"

import pytest


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
