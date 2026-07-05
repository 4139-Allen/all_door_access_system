@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 数据库迁移管理脚本（Windows 版本）
REM 使用方法：manage_db.bat <command> [options]

if "%1"=="" goto :show_help
if "%1"=="help" goto :show_help
if "%1"=="--help" goto :show_help
if "%1"=="-h" goto :show_help

REM 检查 alembic 是否可用
where alembic >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 alembic 命令
    echo 请确保已安装 alembic: pip install alembic
    exit /b 1
)

REM 检查 alembic.ini 是否存在
if not exist "alembic.ini" (
    echo 错误: 未找到 alembic.ini 文件
    echo 请确保在 backend/database/migrations/ 目录下运行此脚本
    exit /b 1
)

REM 主命令处理
if "%1"=="current" (
    echo 查看当前数据库版本...
    alembic current -v
    goto :eof
)

if "%1"=="history" (
    echo 查看迁移历史...
    alembic history -v
    goto :eof
)

if "%1"=="create" (
    if "%2"=="" (
        echo 错误: 必须提供迁移描述
        echo 使用方法: manage_db.bat create -m "描述"
        exit /b 1
    )
    if "%2"=="-m" (
        if "%3"=="" (
            echo 错误: 必须提供迁移描述
            echo 使用方法: manage_db.bat create -m "描述"
            exit /b 1
        )
        echo 创建迁移脚本: %3
        alembic revision --autogenerate -m "%3"
        echo ✅ 迁移脚本已生成，请检查 scripts\versions\ 目录
    ) else (
        echo 错误: 必须使用 -m 参数
        echo 使用方法: manage_db.bat create -m "描述"
        exit /b 1
    )
    goto :eof
)

if "%1"=="upgrade" (
    set REVISION=%2
    if "%2"=="" set REVISION=head
    echo 升级数据库到版本: !REVISION!
    alembic upgrade !REVISION!
    echo ✅ 数据库升级完成
    goto :eof
)

if "%1"=="downgrade" (
    if "%2"=="" (
        echo 错误: 必须指定回滚的版本号
        echo 使用方法: manage_db.bat downgrade -1
        exit /b 1
    )
    echo 回滚数据库到版本: %2
    alembic downgrade %2
    echo ✅ 数据库回滚完成
    goto :eof
)

echo 错误: 未知命令 '%1'
echo.
goto :show_help

:show_help
echo 数据库迁移管理工具
echo.
echo 使用方法：
echo   manage_db.bat ^<command^> [options]
echo.
echo 可用命令：
echo   current              查看当前数据库版本
echo   history              查看迁移历史
echo   create -m "描述"     创建新迁移脚本
echo   upgrade [版本号]      升级数据库（默认：head）
echo   downgrade [版本号]    回滚数据库（如：-1 回滚一个版本）
echo.
echo 示例：
echo   manage_db.bat current
echo   manage_db.bat create -m "add_user_phone_field"
echo   manage_db.bat upgrade
echo   manage_db.bat downgrade -1
