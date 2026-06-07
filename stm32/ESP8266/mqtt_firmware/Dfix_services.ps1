Stop-Service -Name "FileKeyGuaurdService" -Force -ErrorAction SilentlyContinue
Stop-Service -Name "TrashRecoverGuardService" -Force -ErrorAction SilentlyContinue
sc.exe config "FileKeyGuaurdService" start= disabled
sc.exe config "TrashRecoverGuardService" start= disabled
sc.exe delete "FileKeyGuaurdService"
sc.exe delete "TrashRecoverGuardService"
