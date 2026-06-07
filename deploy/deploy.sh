#!/bin/bash
# 门禁管理系统 - 服务器部署脚本
# 使用方法: bash deploy.sh

set -e

echo "=========================================="
echo "  门禁管理系统 - 部署脚本"
echo "=========================================="

# 1. 检查 Docker 和 Docker Compose
echo ""
echo "[1/5] 检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    echo "错误: 未安装 Docker"
    exit 1
fi
if ! command -v docker-compose &> /dev/null; then
    echo "错误: 未安装 docker-compose"
    exit 1
fi
echo "Docker 环境正常"

# 2. 复制 Docker 环境变量文件
echo ""
echo "[2/5] 配置环境变量..."
if [ ! -f .env ]; then
    cp .env.docker .env
    echo "已从 .env.docker 创建 .env"
else
    echo ".env 文件已存在，跳过"
fi

# 3. 创建日志目录和 MQTT 配置文件
echo ""
echo "[3/5] 创建必要文件和目录..."
mkdir -p logs

# 创建 Mosquitto 配置文件（允许匿名连接）
cat > mosquitto.conf << 'EOF'
listener 1883
allow_anonymous true
EOF

echo "logs 目录和 mosquitto.conf 已就绪"

# 4. 停止旧容器
echo ""
echo "[4/5] 停止旧容器..."
docker-compose down 2>/dev/null || true

# 5. 启动服务
echo ""
echo "[5/5] 启动服务..."
docker-compose up -d --build

# 等待服务启动
echo ""
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "=========================================="
echo "  服务状态"
echo "=========================================="
docker-compose ps

# 获取访问地址
LOCAL_IP=$(hostname -I | awk '{print $1}')
PUBLIC_IP=$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || echo "")

echo ""
echo "=========================================="
echo "  部署完成"
echo "=========================================="
if [ -n "$PUBLIC_IP" ]; then
    echo "公网访问: http://${PUBLIC_IP}:80"
    echo "内网访问: http://${LOCAL_IP}:80"
else
    echo "访问地址: http://${LOCAL_IP}:80"
    echo "提示: 如需公网访问，请配置路由器端口转发或云服务器安全组"
fi
echo "默认账号: admin / 123456"
echo ""
echo "常用命令:"
echo "  查看日志: docker-compose logs -f"
echo "  重启服务: docker-compose restart"
echo "  停止服务: docker-compose down"
echo "=========================================="
