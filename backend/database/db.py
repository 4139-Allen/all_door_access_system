import re
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

    except Exception as e:
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

