@echo off
echo ========================================
echo    恶意软件清理脚本 (管理员权限)
echo ========================================
echo.

echo [1/7] 删除 EchoFindSearch...
rd /s /q "C:\Program Files (x86)\EchoFindSearch" 2>/dev/null
if exist "C:\Program Files (x86)\EchoFindSearch" (echo   [!] 需重启删除) else (echo   [OK] 已删除)

echo [2/7] 删除 FileKey + SafeKey...
rd /s /q "C:\Program Files (x86)\FileKey" 2>/dev/null
rd /s /q "C:\Users\laichangjian\AppData\Roaming\SafeKey" 2>/dev/null
rd /s /q "C:\Users\laichangjian\AppData\Local\FileKey" 2>/dev/null
if exist "C:\Program Files (x86)\FileKey" (echo   [!] FileKey 需重启删除) else (echo   [OK] FileKey 已删除)
if exist "C:\Users\laichangjian\AppData\Roaming\SafeKey" (echo   [!] SafeKey 需重启删除) else (echo   [OK] SafeKey 已删除)

echo [3/7] 删除 TrashRecover...
rd /s /q "C:\Users\laichangjian\AppData\Roaming\TrashRecover" 2>/dev/null
rd /s /q "C:\Users\laichangjian\AppData\Roaming\TrashRecoverCfg" 2>/dev/null
if exist "C:\Users\laichangjian\AppData\Roaming\TrashRecover" (echo   [!] 需重启删除) else (echo   [OK] 已删除)

echo [4/7] 删除 LhpNetSentinel...
rd /s /q "C:\Program Files (x86)\LhpNetSentinel" 2>/dev/null
if exist "C:\Program Files (x86)\LhpNetSentinel" (echo   [!] 需重启删除) else (echo   [OK] 已删除)

echo [5/7] 删除恶意服务...
sc stop FileKeyGuaurdService 2>/dev/null
sc stop TrashRecoverGuardService 2>/dev/null
sc delete FileKeyGuaurdService 2>/dev/null
sc delete TrashRecoverGuardService 2>/dev/null
echo   [OK] 服务已处理

echo [6/7] 清理注册表启动项...
reg delete "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run" /v "360Safetray" /f 2>/dev/null
reg delete "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run" /v "kxesc" /f 2>/dev/null
echo   [OK] 注册表已清理

echo [7/7] 清理临时脚本...
del /f /q "D:\reboot_cleanup.bat" 2>/dev/null
del /f /q "D:\cleanup_services.ps1" 2>/dev/null
del /f /q "D:\fix_services.ps1" 2>/dev/null
del /f /q "D:\del_malware.ps1" 2>/dev/null
del /f /q "D:\del_all.bat" 2>/dev/null
del /f /q "D:\cleanup3.ps1" 2>/dev/null
echo   [OK] 临时脚本已清理

echo.
echo ========================================
echo    清理完成！
echo ========================================
echo.
echo 如果显示"需重启删除"，请再次重启电脑
echo 重启后恶意软件将被彻底清除
echo.
pause
