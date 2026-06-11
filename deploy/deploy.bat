@echo off
chcp 65001 >nul
title 门禁管理系统 - 部署脚本

echo ==========================================
echo   门禁管理系统 - 部署脚本
echo ==========================================

REM 1. 检查 Docker
echo.
echo [1/5] 检查 Docker 环境...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未安装 Docker
    pause
    exit /b 1
)

REM 检查 Docker Compose V2（docker compose）
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未安装 Docker Compose V2
    echo 请安装 Docker Compose V2: https://docs.docker.com/compose/install/
    pause
    exit /b 1
)
echo Docker 环境正常

REM 2. 复制环境变量
echo.
echo [2/5] 配置环境变量...
if not exist .env (
    copy .env.docker .env
    echo 已从 .env.docker 创建 .env
) else (
    echo .env 文件已存在，跳过
)

REM 3. 创建日志目录和 MQTT 配置文件
echo.
echo [3/5] 创建必要文件和目录...
if not exist logs mkdir logs

REM 创建 Mosquitto 配置文件（允许匿名连接）
echo listener 1883 > mosquitto.conf
echo allow_anonymous true >> mosquitto.conf

echo logs 目录和 mosquitto.conf 已就绪

REM 4. 停止旧容器
echo.
echo [4/5] 停止旧容器...
docker compose down 2>nul

REM 5. 启动服务
echo.
echo [5/5] 启动服务...
docker compose up -d --build

echo.
echo 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo.
echo ==========================================
echo   服务状态
echo ==========================================
docker compose ps

echo.
echo ==========================================
echo   部署完成
echo ==========================================

REM 获取本机IP地址
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP: =%

echo 访问地址: http://%LOCAL_IP%:80
echo 提示: 如需公网访问，请配置路由器端口转发或云服务器安全组
echo 默认账号: admin / 123456
echo.
echo 常用命令:
echo   查看日志: docker compose logs -f
echo   重启服务: docker compose restart
echo   停止服务: docker compose down
echo ==========================================
pause
