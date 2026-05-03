#  清除資源回收桶資料
$RecycleBinPath = "$env:USERPROFILE\$Recycle.Bin"
if (Test-Path $RecycleBinPath) {
    Get-ChildItem -Path $RecycleBinPath -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
    Write-Host "Recycle Bin cleared."
}