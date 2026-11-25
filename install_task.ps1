# 注册 / 查看 / 删除 TECI 的每日自动更新任务（Windows 计划任务）
#
# 用法：
#   .\install_task.ps1                 默认每天 09:30 更新
#   .\install_task.ps1 -At "21:15"     指定时间
#   .\install_task.ps1 -Status         查看状态和上次运行结果
#   .\install_task.ps1 -Remove         删除任务
#
# 任务调用 daily_run.cmd（内部再调 run.cmd -NoOpen）：
#   抓价 -> 算指数 -> 生成网页，不开浏览器。
# 错过时间点会在下次开机后补跑（StartWhenAvailable）。

param(
    [string]$At = "09:30",
    [switch]$Remove,
    [switch]$Status
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = "TECI_Daily"
$target = Join-Path $root "daily_run.cmd"

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

if ($Status) {
    $t = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $t) {
        Write-Host "任务 $taskName 不存在。请双击 install_task.cmd 创建。" -ForegroundColor Yellow
        exit 1
    }
    $i = Get-ScheduledTaskInfo -TaskName $taskName
    Write-Host "任务名称 : $taskName"
    Write-Host "状态     : $($t.State)"
    Write-Host "下次运行 : $($i.NextRunTime)"
    Write-Host "上次运行 : $($i.LastRunTime)"
    Write-Host "上次结果 : $($i.LastTaskResult)   (0 = 成功，1 = 脚本报错)"
    Write-Host ""
    Write-Host "详细日志 : logs\run.log" -ForegroundColor DarkGray
    exit 0
}

if ($Remove) {
    $t = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $t) { Write-Host "任务 $taskName 不存在，无需删除。" -ForegroundColor Yellow; exit 0 }
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "已删除计划任务 $taskName" -ForegroundColor Green
    exit 0
}

if (-not (Test-Path $target)) { throw "找不到 $target" }
if ($At -notmatch '^\d{1,2}:\d{2}$') { throw "时间格式应为 HH:mm，例如 09:30" }

Write-Host "正在注册每日任务：每天 $At 运行 $target" -ForegroundColor Cyan

$registered = $false

# 首选：计划任务 cmdlet（可以设置 missed-run 补跑）
try {
    $action = New-ScheduledTaskAction -Execute $target -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -Daily -At $At
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
        -Settings $settings -Force `
        -Description "TECI 每日更新：抓取价格 -> 计算指数 -> 生成网页" | Out-Null
    $registered = $true
    Write-Host "已通过 Register-ScheduledTask 注册。" -ForegroundColor DarkGray
}
catch {
    Write-Host "cmdlet 注册失败（$($_.Exception.Message)），改用 schtasks…" -ForegroundColor DarkGray
}

# 备用：schtasks（非管理员有时反而可用）
if (-not $registered) {
    & schtasks.exe /Create /SC DAILY /ST $At /TN $taskName /TR $target /F | Out-Host
    if ($LASTEXITCODE -eq 0) { $registered = $true }
}

if (-not $registered) {
    Write-Host ""
    Write-Host "两种方式都没成功。" -ForegroundColor Red
    Write-Host "请右键 install_task.cmd，选择「以管理员身份运行」再试一次。" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "注册成功。" -ForegroundColor Green
try {
    $i = Get-ScheduledTaskInfo -TaskName $taskName
    Write-Host "下次运行：$($i.NextRunTime)"
} catch {}

Write-Host ""
Write-Host "想确认能跑通，先手动执行一次：  run.cmd -NoOpen" -ForegroundColor DarkGray
Write-Host "之后查看运行结果：              .\install_task.ps1 -Status" -ForegroundColor DarkGray
