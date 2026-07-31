import re
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import DATABASE_URL
from utils.logger import AppLogger

logger = AppLogger.get_logger() #统一的日志记录

if not DATABASE_URL:
    raise ValueError("未找到 DATABASE_URL 环境变量！\n请在 .env 文件中配置数据库连接")

#连接池配置
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,           # 连接池大小
    max_overflow=20,        # 最大溢出连接数
    pool_recycle=3600,      # 连接回收时间（秒）
    pool_pre_ping=True      # 连接前检查是否有效
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()   # 创建基类

# ==================== 数据库初始化逻辑 ====================
def init_database():
    """
    启动时自动检查并创建数据库，然后统一由 Alembic 管理表结构

    策略（纯 Alembic 版本管理，已取消 create_all）：
    - 数据库不存在：自动创建数据库
    - 空库（无 alembic_version）：alembic upgrade head 会从头执行初始迁移，
      建出全部表并记录版本
    - 已有库：alembic upgrade head 增量迁移到最新版本（幂等）
    - 所有表结构变更都必须通过迁移脚本（manage_db.py create/upgrade）
    """
    import time

    max_retries = 30
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            # 1. 提取基础连接串和数据库名
            match = re.match(r"(mysql\+pymysql://[^/]+)/(.+)", DATABASE_URL)
            if match:
                base_url, db_name = match.group(1), match.group(2)

                # 连接到 MySQL 服务器（不指定具体数据库）
                temp_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
                try:
                    with temp_engine.connect() as conn:
                        # 自动建库（如果不存在）
                        conn.execute(text(
                            f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                        logger.info(f"🗄️ 数据库 '{db_name}' 检查/创建成功")
                finally:
                    temp_engine.dispose()
            break

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"⏳ 数据库连接失败，{retry_delay}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                time.sleep(retry_delay)
            else:
                logger.error(f"💥 数据库初始化失败: {e}")
                raise

    # 2. 执行 Alembic 迁移到最新版本（空库建全表 / 已有库增量迁移，均幂等）
    run_alembic_migrations()


# 依赖注入（给FastAPI用）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== Alembic 数据库迁移 ====================
# 使用说明：
# 1. 当需要修改表结构时（如增加字段），先修改 SQLAlchemy 模型
# 2. 然后运行（在 backend/database/migrations/ 目录下）：
#    alembic revision --autogenerate -m "描述变更"
# 3. 检查生成的迁移脚本（在 scripts/versions/ 目录下）
# 4. 执行迁移：alembic upgrade head
# 5. 回滚迁移：alembic downgrade -1
#
# 常用命令（在 backend/database/migrations/ 目录下）：
#   alembic current          - 查看当前版本
#   alembic history          - 查看迁移历史
#   alembic upgrade head     - 升级到最新版本
#   alembic downgrade -1     - 回滚一个版本
#   alembic upgrade +2       - 升级两个版本
#
# 或者使用管理脚本（在 backend/database/migrations/ 目录下）：
#   python manage_db.py current
#   python manage_db.py create -m "add_phone_field"
#   python manage_db.py upgrade
#   python manage_db.py downgrade -1


def _get_alembic_config():
    """获取 Alembic 配置（找不到 alembic.ini 时返回 None）"""
    from alembic.config import Config

    # 获取 alembic.ini 的路径（位于 database/migrations/ 下）
    alembic_ini_path = os.path.join(os.path.dirname(__file__), 'migrations', 'alembic.ini')

    if not os.path.exists(alembic_ini_path):
        logger.warning("⚠️ alembic.ini 不存在，跳过 Alembic 迁移")
        return None

    return Config(alembic_ini_path)


def _fix_stale_alembic_revision():
    """修复失效的 Alembic 版本号

    场景：旧迁移文件被删除/squash 后，数据库 alembic_version 仍指向旧版本号，
    此时 alembic upgrade 会报 "Can't locate revision"。检测到这种情况就把
    版本号 stamp 到 head，让 upgrade 变成幂等操作。
    """
    try:
        from sqlalchemy import inspect as sa_inspect

        # 该表不存在说明从没做过 Alembic 迁移，无需修复
        if "alembic_version" not in sa_inspect(engine).get_table_names():
            return

        from sqlalchemy import text
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        current_version = row[0] if row else None
        if not current_version:
            return

        alembic_cfg = _get_alembic_config()
        if alembic_cfg is None:
            return

        from alembic.script import ScriptDirectory
        script = ScriptDirectory.from_config(alembic_cfg)
        revisions = {r.revision for r in script.walk_revisions()}

        if current_version not in revisions:
            logger.warning(
                f"⚠️ 检测到失效的 Alembic 版本号 {current_version}，"
                f"stamp 到 head 后继续迁移"
            )
            from alembic import command
            # purge=True：先清空失效版本号再写入 head，
            # 否则 stamp/upgrade 会先解析旧版本号而报 "Can't locate revision"
            command.stamp(alembic_cfg, "head", purge=True)
    except Exception as e:
        # 修复失败不阻塞启动，交给后续 upgrade 报错
        logger.warning(f"⚠️ 修复失效 Alembic 版本号失败: {e}")


def run_alembic_migrations():
    """执行 Alembic 数据库迁移（升级到最新版本）"""
    try:
        alembic_cfg = _get_alembic_config()
        if alembic_cfg is None:
            return

        from alembic import command

        # 修复因旧迁移被 squash 而产生的失效版本号
        _fix_stale_alembic_revision()

        # 执行迁移到最新版本
        command.upgrade(alembic_cfg, "head")

        # 保险：alembic 的 fileConfig 可能禁用过应用 logger，这里幂等地恢复，
        # 确保迁移后业务日志、请求日志继续输出
        import logging
        logging.getLogger("app").disabled = False

        logger.info("✅ Alembic 迁移完成")

    except Exception as e:
        logger.error(f"⚠️ Alembic 迁移失败: {e}")
        raise

