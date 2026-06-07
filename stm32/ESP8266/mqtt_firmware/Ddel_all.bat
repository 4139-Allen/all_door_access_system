@echo off
rd /s /q "C:\Program Files (x86)\EchoFindSearch"
rd /s /q "C:\Program Files (x86)\FileKey"
rd /s /q "C:\Users\laichangjian\AppData\Roaming\SafeKey"
rd /s /q "C:\Users\laichangjian\AppData\Local\FileKey"
rd /s /q "C:\Users\laichangjian\AppData\Roaming\TrashRecover"
rd /s /q "C:\Users\laichangjian\AppData\Roaming\TrashRecoverCfg"
rd /s /q "C:\Program Files (x86)\LhpNetSentinel"
sc delete FileKeyGuaurdService
sc delete TrashRecoverGuardService
