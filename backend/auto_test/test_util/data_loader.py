"""
测试数据加载器

职责：
  1. 从 data/ 目录加载 JSON / YAML 测试数据
  2. 支持模板变量替换（如 __name__ 自动生成唯一值）
  3. 支持参数化数据源，直接配合 @pytest.mark.parametrize
  4. 后续可扩展支持 Excel / CSV 格式

用法：
    from test_util.data_loader import load_cases, build_request

    # 加载所有测试用例
    cases = load_cases("login", "success_cases.json")

    @pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
    def test_login(case):
        resp = client.post("/auth/login", json=build_request(case))
        assert resp.json()["code"] == case["expect"]["code"]

    # 带模板变量替换
    case = build_request(load_cases("device", "create_cases.json")[0],
                         name="AUTO-TEST-DOOR-001",
                         location="自动化测试-正门")

路径规则：
    data/login/success_cases.json  →  load_cases("login", "success_cases.json")
    data/device/create_cases.json  →  load_cases("device", "create_cases.json")
"""
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# data/ 目录的绝对路径
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ── 核心加载方法 ─────────────────────────────────


def load_cases(module: str, filename: str, encoding: str = "utf-8") -> List[Dict]:
    """
    加载测试数据文件

    参数：
        module:   子目录名（如 "login", "device", "user"）
        filename: 文件名（如 "success_cases.json", "failure_cases.yaml"）
        encoding: 文件编码（默认 utf-8）

    返回：
        用例列表，每个元素是一个 dict

    支持格式：
        .json  →  JSON 标准格式
        .yaml  →  YAML 格式（需安装 PyYAML）

    用法：
        cases = load_cases("login", "success_cases.json")
        for case in cases:
            print(case["title"])
    """
    filepath = DATA_DIR / module / filename

    if not filepath.exists():
        raise FileNotFoundError(
            f"测试数据文件不存在: {filepath}\n"
            f"预期路径: data/{module}/{filename}"
        )

    suffix = filepath.suffix.lower()

    if suffix == ".json":
        return _load_json(filepath, encoding)
    elif suffix in (".yaml", ".yml"):
        return _load_yaml(filepath, encoding)
    else:
        raise ValueError(
            f"不支持的文件格式: {suffix}（支持: .json, .yaml, .yml）"
            f"\n如需支持新格式，请在 {__file__} 中添加对应加载方法"
        )


# ── 构建测试请求 ─────────────────────────────────


def build_request(
    case: Dict,
    **variables,
) -> Dict:
    """
    从测试用例模板构建请求体

    替换 request 中的 __xxx__ 占位符：
      - __name__     → 替换为 variables 中 name 的值（或自动生成唯一值）
      - __username__ → 替换为 variables 中 username 的值
      - __location__ → 替换为 variables 中 location 的值
      - __suffix__   → 替换为 8 位随机 hex 字符串

    参数：
        case:      用例 dict（含 request 字段）
        variables: 模板变量键值对

    返回：
        替换完成的 request dict

    用法：
        case = load_cases("device", "create_cases.json")[0]
        body = build_request(case, name="AUTO-TEST-DOOR-01")
        client.post("/devices", json=body)
    """
    request_body = case.get("request", {}).copy()

    for key, value in request_body.items():
        if isinstance(value, str) and value.startswith("__") and value.endswith("__"):
            request_body[key] = _resolve_placeholder(value, key, variables)

    return request_body


# ── 变量解析 ────────────────────────────────────


def _resolve_placeholder(placeholder: str, field_name: str, variables: Dict) -> str:
    """解析单个占位符"""
    # 如果有显式变量值，优先用
    if field_name in variables:
        return str(variables[field_name])

    # 内置占位符
    if placeholder == "__suffix__":
        return uuid.uuid4().hex[:8]
    if placeholder in ("__name__", "__username__", "__location__"):
        # 自动生成默认值（统一 auto_test_ 前缀）
        defaults = {
            "__name__": f"auto_test_device_{uuid.uuid4().hex[:8]}",
            "__username__": f"auto_test_user_{uuid.uuid4().hex[:8]}",
            "__location__": "自动化测试-位置",
        }
        return defaults[placeholder]

    return placeholder


# ── 文件格式解析 ─────────────────────────────────


def _load_json(filepath: Path, encoding: str) -> List[Dict]:
    """加载 JSON 文件"""
    with open(filepath, encoding=encoding) as f:
        data = json.load(f)

    cases = data.get("cases", data)
    if isinstance(cases, dict):
        cases = [cases]
    return cases


def _load_yaml(filepath: Path, encoding: str) -> List[Dict]:
    """加载 YAML 文件"""
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "加载 YAML 文件需要安装 PyYAML: pip install pyyaml"
        )

    with open(filepath, encoding=encoding) as f:
        data = yaml.safe_load(f)

    cases = data.get("cases", data)
    if isinstance(cases, dict):
        cases = [cases]
    return cases


# ── 便捷方法（后续扩展） ─────────────────────────


def load_cases_from_excel(module: str, filename: str) -> List[Dict]:
    """
    从 Excel 加载测试数据（预留，后续实现）

    需要的库：openpyxl（项目中已有）
    """
    raise NotImplementedError("Excel 数据加载功能待实现")


def load_cases_from_csv(module: str, filename: str) -> List[Dict]:
    """
    从 CSV 加载测试数据（预留，后续实现）
    """
    raise NotImplementedError("CSV 数据加载功能待实现")
