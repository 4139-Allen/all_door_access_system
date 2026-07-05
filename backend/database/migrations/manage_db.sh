#!/bin/bash
# 数据库迁移管理脚本（Shell 版本）
# 使用方法：bash manage_db.sh <command> [options]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印帮助信息
show_help() {
    echo "数据库迁移管理工具"
    echo ""
    echo "使用方法："
    echo "  bash manage_db.sh <command> [options]"
    echo ""
    echo "可用命令："
    echo "  current              查看当前数据库版本"
    echo "  history              查看迁移历史"
    echo "  create -m \"描述\"     创建新迁移脚本"
    echo "  upgrade [版本号]      升级数据库（默认：head）"
    echo "  downgrade [版本号]    回滚数据库（如：-1 回滚一个版本）"
    echo ""
    echo "示例："
    echo "  bash manage_db.sh current"
    echo "  bash manage_db.sh create -m \"add_user_phone_field\""
    echo "  bash manage_db.sh upgrade"
    echo "  bash manage_db.sh downgrade -1"
}

# 检查 alembic 是否可用
check_alembic() {
    if ! command -v alembic &> /dev/null; then
        echo -e "${RED}错误: 未找到 alembic 命令${NC}"
        echo "请确保已安装 alembic: pip install alembic"
        exit 1
    fi
}

# 检查 alembic.ini 是否存在
check_config() {
    if [ ! -f "alembic.ini" ]; then
        echo -e "${RED}错误: 未找到 alembic.ini 文件${NC}"
        echo -e "请确保在 backend/database/migrations/ 目录下运行此脚本"
        exit 1
    fi
}

# 主命令处理
case "$1" in
    current)
        check_alembic
        check_config
        echo -e "${GREEN}查看当前数据库版本...${NC}"
        alembic current -v
        ;;
    history)
        check_alembic
        check_config
        echo -e "${GREEN}查看迁移历史...${NC}"
        alembic history -v
        ;;
    create)
        check_alembic
        check_config
        if [ -z "$2" ] || [ "$2" != "-m" ] || [ -z "$3" ]; then
            echo -e "${RED}错误: 必须提供迁移描述${NC}"
            echo "使用方法: bash manage_db.sh create -m \"描述\""
            exit 1
        fi
        echo -e "${GREEN}创建迁移脚本: $3${NC}"
        alembic revision --autogenerate -m "$3"
        echo -e "${GREEN}✅ 迁移脚本已生成，请检查 scripts/versions/ 目录${NC}"
        ;;
    upgrade)
        check_alembic
        check_config
        REVISION=${2:-head}
        echo -e "${GREEN}升级数据库到版本: $REVISION${NC}"
        alembic upgrade "$REVISION"
        echo -e "${GREEN}✅ 数据库升级完成${NC}"
        ;;
    downgrade)
        check_alembic
        check_config
        if [ -z "$2" ]; then
            echo -e "${RED}错误: 必须指定回滚的版本号${NC}"
            echo "使用方法: bash manage_db.sh downgrade -1"
            exit 1
        fi
        echo -e "${YELLOW}回滚数据库到版本: $2${NC}"
        alembic downgrade "$2"
        echo -e "${GREEN}✅ 数据库回滚完成${NC}"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}错误: 未知命令 '$1'${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
