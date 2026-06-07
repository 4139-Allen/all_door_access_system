# 停止并禁用恶意服务
$malwareServices = @("FileKeyGuaurdService", "TrashRecoverGuardService")
foreach ($svc in $malwareServices) {
    Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
    sc.exe config $svc start= disabled 2>$null
    sc.exe delete $svc 2>$null
    Write-Output "[OK] 已处理: $svc"
}

# 验证
foreach ($svc in $malwareServices) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($s) { Write-Output "[!] $svc 仍存在: $($s.Status)" } else { Write-Output "[OK] $svc 已删除" }
}
