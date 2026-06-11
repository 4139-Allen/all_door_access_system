#!/usr/bin/env python
"""
数据库迁移管理脚本

使用方法：
    python manage_db.py current          # 查看当前数据库版本
    python manage_db.py history          # 查看迁移历史
    python manage_db.py create -m "描述" # 创建新迁移脚本
    python manage_db.py upgrade          # 升级到最新版本
    python manage_db.py upgrade <版本号>  # 升级到指定版本
    python manage_db.py downgrade -1     # 回滚一个版本
    python manage_db.py downgrade <版本号> # 回滚到指定版本

示例：
    # 1. 修改 SQLAlchemy 模型后，生成迁移脚本
    python manage_db.py create -m "add_user_phone_field"

    # 2. 检查生成的迁移脚本
    # 文件位于 alembic/versions/ 目录下

    # 3. 执行迁移
    python manage_db.py upgrade

    # 4. 如果需要回滚
    python manage_db.py downgrade -1
"""

import argparse
import sys
import os

# 确保当前目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alembic.config import Config
from alembic import command


def get_alembic_config():
    """获取 Alembic 配置"""
    alembic_ini_path = os.path.join(os.path.dirname(__file__), 'alembic.ini')

    if not os.path.exists(alembic_ini_path):
        print("❌ 错误：找不到 alembic.ini 文件")
        print("请确保在 backend/ 目录下运行此脚本")
        sys.exit(1)

    return Config(alembic_ini_path)


def cmd_current(args):
    """查看当前数据库版本"""
    alembic_cfg = get_alembic_config()
    command.current(alembic_cfg, verbose=True)


def cmd_history(args):
    """查看迁移历史"""
    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg, verbose=True)


def cmd_create(args):
    """创建新迁移脚本"""
    if not args.message:
        print("❌ 错误：必须提供迁移描述 (-m 参数)")
        sys.exit(1)

    alembic_cfg = get_alembic_config()

    print(f"📝 正在创建迁移脚本：{args.message}")
    command.revision(alembic_cfg, autogenerate=True, message=args.message)
    print("✅ 迁移脚本已生成，请检查 alembic/versions/ 目录")
    print("💡 提示：请在执行 upgrade 前检查生成的脚本是否正确")


def cmd_upgrade(args):
    """升级数据库"""
    alembic_cfg = get_alembic_config()
    revision = args.revision or 'head'

    print(f"⬆️ 正在升级数据库到版本：{revision}")
    command.upgrade(alembic_cfg, revision)
    print("✅ 数据库升级完成")


def cmd_downgrade(args):
    """回滚数据库"""
    alembic_cfg = get_alembic_config()

    if not args.revision:
        print("❌ 错误：必须指定回滚的版本号")
        print("💡 提示：使用 -1 回滚一个版本，或使用具体版本号")
        sys.exit(1)

    print(f"⬇️ 正在回滚数据库到版本：{args.revision}")
    command.downgrade(alembic_cfg, args.revision)
    print("✅ 数据库回滚完成")


def main():
    parser = argparse.ArgumentParser(
        description='数据库迁移管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # current 命令
    subparsers.add_parser('current', help='查看当前数据库版本')

    # history 命令
    subparsers.add_parser('history', help='查看迁移历史')

    # create 命令
    create_parser = subparsers.add_parser('create', help='创建新迁移脚本')
    create_parser.add_argument('-m', '--message', required=True, help='迁移描述')

    # upgrade 命令
    upgrade_parser = subparsers.add_parser('upgrade', help='升级数据库')
    upgrade_parser.add_argument('revision', nargs='?', default='head', help='目标版本（默认：head）')

    # downgrade 命令
    downgrade_parser = subparsers.add_parser('downgrade', help='回滚数据库')
    downgrade_parser.add_argument('revision', nargs='?', help='目标版本（如：-1 表示回滚一个版本）')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        'current': cmd_current,
        'history': cmd_history,
        'create': cmd_create,
        'upgrade': cmd_upgrade,
        'downgrade': cmd_downgrade,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(f"❌ 错误：{e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
