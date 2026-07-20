#!/usr/bin/env python
"""
自动化测试一键执行入口

用法：
    python run.py                                 # API 测试（需手动启动后端）
    python run.py --type=integration              # 集成测试
    python run.py --type=all                      # API + 集成
    python run.py --type=performance              # 性能测试（Locust）
    python run.py --reset-db                      # 删库重建 + 自动启停后端
    python run.py --reset-db --smoke-only         # 删库重建 + 冒烟测试
"""
import sys
import time
import signal
import subprocess
import argparse
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def reset_test_db():
    """重建测试数据库"""
    print("[DB] 重建测试数据库 door_access_test...")
    try:
        import pymysql
        conn = pymysql.connect(
            host="127.0.0.1", port=3306, user="root", password="123456"
        )
        conn.cursor().execute("DROP DATABASE IF EXISTS door_access_test")
        conn.cursor().execute("CREATE DATABASE door_access_test CHARACTER SET utf8mb4")
        conn.close()
        print("[OK] 测试库已重建")
        return True
    except ImportError:
        print("[WARN] 未安装 pymysql，跳过删库")
        return False
    except Exception as e:
        print(f"[ERR] 重建测试库失败: {e}")
        return False


def start_backend(with_coverage: bool = False, data_file: Path = None, log_dir: str = None):
    """启动后端服务"""
    print("[START] 启动后端服务..." + ("（覆盖率模式）" if with_coverage else ""))
    if with_coverage:
        data_file.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable, "-m", "coverage", "run",
            "--source=api,services,utils,core",
            f"--data-file={data_file}",
            "-m", "main"
        ]
    else:
        cmd = [sys.executable, "main.py"]
    env = {**__import__('os').environ, "MYSQL_DB": "door_access_test"}
    if log_dir:
        env["LOG_DIR"] = log_dir
    proc = subprocess.Popen(
        cmd, cwd=BACKEND_DIR, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return proc


def wait_for_ready(url: str, timeout: int = 30) -> bool:
    """等待后端就绪"""
    import urllib.request
    for i in range(timeout):
        try:
            resp = urllib.request.urlopen(f"{url}/api/health", timeout=2)
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    parser = argparse.ArgumentParser(description="门禁系统自动化测试")
    parser.add_argument("--type", default="api", choices=["api", "integration", "performance", "all"],
                        help="测试类型: api(模块)/integration(集成)/performance(性能)/all(全部)")
    parser.add_argument("--reset-db", action="store_true", help="删库重建 + 自动启停后端")
    parser.add_argument("--coverage", action="store_true", help="开启后端代码覆盖率")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--parallel", type=int, default=0)
    parser.add_argument("extra_args", nargs="*")
    args = parser.parse_args()

    reports_dir = Path(__file__).parent / "reports" / "test"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # ===== 删库 + 启动后端（--reset-db 时开启） =====
    backend_proc = None
    if args.reset_db:
        if not reset_test_db():
            sys.exit(1)
        log_dir = reports_dir / "logs"
        if log_dir.exists():
            import shutil
            shutil.rmtree(log_dir)
            print("[LOG] 测试日志已清理")
        cov_data = reports_dir / ".coverage" if args.coverage else None
        backend_proc = start_backend(
            with_coverage=args.coverage, data_file=cov_data,
            log_dir=str(reports_dir / "logs")
        )
        base_url = "http://127.0.0.1:8000"
        print("[WAIT] 等待后端就绪...", end="", flush=True)
        if not wait_for_ready(base_url):
            print("\n[ERR] 后端启动超时")
            backend_proc.kill()
            sys.exit(1)
        print(" [OK]")

    # ===== 根据 --type 选择测试目录 =====
    type_map = {
        "api": ["cases/"],
        "integration": ["integration/"],
        "performance": ["performance/locustfile.py"],
        "all": ["cases/", "integration/"],
    }
    test_paths = type_map.get(args.type, ["cases/"])

    # ===== 拼装 pytest 命令 =====
    pytest_cmd = [
        sys.executable, "-m", "pytest", *test_paths,
        "-v", "--tb=short",
    ]

    pytest_cmd.append(f"--junitxml={reports_dir / 'junit.xml'}")
    pytest_cmd.append(f"--alluredir={reports_dir / 'allure'}")

    if args.smoke_only:
        pytest_cmd.extend(["-m", "smoke"])
    if args.parallel > 0:
        pytest_cmd.extend(["-n", str(args.parallel)])
    if args.extra_args:
        pytest_cmd.extend(args.extra_args)

    print(f"[RUN] 类型: {args.type} | 报告: {reports_dir} {'| 已删库+自动启停' if args.reset_db else ''}")
    print(f"[RUN] {' '.join(pytest_cmd)}")

    # ===== 执行测试 =====
    cwd = Path(__file__).parent
    result = subprocess.run(pytest_cmd, cwd=cwd)

    # ===== 清理后端 =====
    if backend_proc:
        print("[STOP] 关闭后端服务...")
        if sys.platform == "win32":
            # 注意: CTRL_C_EVENT 在 Windows 上会传播到整个控制台进程组，
            # 导致父进程也收到 KeyboardInterrupt，所以用 try 包裹
            try:
                backend_proc.send_signal(signal.CTRL_C_EVENT)
                backend_proc.wait()
            except KeyboardInterrupt:
                # 信号已传播到父进程，子进程已经退出
                pass
        else:
            backend_proc.terminate()
            backend_proc.wait()

    # ===== 覆盖率报告 =====
    cov_data = reports_dir / ".coverage"
    if args.coverage and backend_proc and cov_data.exists():
        print("[COV] 生成覆盖率报告...")
        subprocess.run([
            sys.executable, "-m", "coverage", "report",
            f"--data-file={cov_data}",
            "--show-missing",
        ], cwd=BACKEND_DIR)
        subprocess.run([
            sys.executable, "-m", "coverage", "html",
            f"--data-file={cov_data}",
            f"--directory={reports_dir / 'coverage_html'}",
        ], cwd=BACKEND_DIR)
        print(f"[COV] HTML 报告: {reports_dir / 'coverage_html' / 'index.html'}")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
