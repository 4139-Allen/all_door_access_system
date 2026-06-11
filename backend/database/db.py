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
    """启动时自动检查并创建数据库和数据表"""
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

            # 2. 自动建表（如果不存在）
            Base.metadata.create_all(bind=engine)
            logger.info("📋 数据表初始化完成")
            return

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"⏳ 数据库连接失败，{retry_delay}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                time.sleep(retry_delay)
            else:
                logger.error(f"💥 数据库初始化失败: {e}")
                raise

def drop_all_tables():
    """⚠️ 警告：删除所有表！仅用于开发环境重置数据库"""
    try:
        logger.warning("🗑️ 正在执行删除所有表操作...")
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ 所有表已删除")
    except Exception as e:
        logger.error(f"💥 删除表失败: {e}")
        raise


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
# 2. 然后运行：alembic revision --autogenerate -m "描述变更"
# 3. 检查生成的迁移脚本（在 alembic/versions/ 目录下）
# 4. 执行迁移：alembic upgrade head
# 5. 回滚迁移：alembic downgrade -1
#
# 常用命令：
#   alembic current          - 查看当前版本
#   alembic history          - 查看迁移历史
#   alembic upgrade head     - 升级到最新版本
#   alembic downgrade -1     - 回滚一个版本
#   alembic upgrade +2       - 升级两个版本
#
# 或者使用管理脚本：
#   python manage_db.py current
#   python manage_db.py create -m "add_phone_field"
#   python manage_db.py upgrade
#   python manage_db.py downgrade -1

def run_alembic_migrations():
    """执行 Alembic 数据库迁移（可选，用于生产环境）"""
    try:
        from alembic.config import Config
        from alembic import command

        # 获取 alembic.ini 的路径
        alembic_ini_path = os.path.join(os.path.dirname(__file__), '..', 'alembic.ini')

        if not os.path.exists(alembic_ini_path):
            logger.warning("⚠️ alembic.ini 不存在，跳过 Alembic 迁移")
            return

        alembic_cfg = Config(alembic_ini_path)

        # 执行迁移到最新版本
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Alembic 迁移完成")

    except Exception as e:
        logger.warning(f"⚠️ Alembic 迁移失败（可忽略，如果使用 create_all）: {e}")
        raise

