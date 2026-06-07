@echo off
timeout /t 20 /nobreak > /dev/null

:: 删除恶意软件目录
rd /s /q "C:\Program Files (x86)\EchoFindSearch" 2>/dev/null
rd /s /q "C:\Program Files (x86)\FileKey" 2>/dev/null
rd /s /q "C:\Users\laichangjian\AppData\Roaming\SafeKey" 2>/dev/null
rd /s /q "C:\Users\laichangjian\AppData\Local\FileKey" 2>/dev/null
rd /s /q "C:\Users\laichangjian\AppData\Roaming\TrashRecover" 2>/dev/null
rd /s /q "C:\Users\laichangjian\AppData\Roaming\TrashRecoverCfg" 2>/dev/null
rd /s /q "C:\Program Files (x86)\LhpNetSentinel" 2>/dev/null

:: 删除恶意服务
sc delete FileKeyGuaurdService 2>/dev/null
sc delete TrashRecoverGuardService 2>/dev/null

:: 清理注册表启动项
reg delete "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run" /v "360Safetray" /f 2>/dev/null
reg delete "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run" /v "kxesc" /f 2>/dev/null

:: 自删除
del /f /q "D:\reboot_cleanup.bat" 2>/dev/null
