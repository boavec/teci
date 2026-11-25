# 一键更新 TECI：抓价格 -> 算指数 -> 生成网页
# 用法：
#   .\run.ps1              抓数据并重建，完成后打开网页
#   .\run.ps1 -NoOpen      只重建，不开浏览器（给计划任务用）
#   .\run.ps1 -SkipFetch   不联网，只用已有快照重建
#
# 每次运行都会写 logs/run.log，便于回头查哪天失败了。

param(
    [switch]$NoOpen,
    [switch]$SkipFetch
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "run.log"

function Write-Log([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

# 日志超过 1MB 就轮转，避免无限增长
if ((Test-Path $logFile) -and (Get-Item $logFile).Length -gt 1MB) {
    Move-Item -Path $logFile -Destination ($logFile + ".1") -Force
}

try {
    $env:PYTHONIOENCODING = "utf-8"
    try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

    $python = "python"
    Write-Log "=== START (SkipFetch=$SkipFetch NoOpen=$NoOpen) ==="

    if (-not $SkipFetch) {
        Write-Host "== 1/2  抓取最新价格 ==" -ForegroundColor Cyan
        $fetchOut = & $python scripts\fetch_models.py 2>&1 | Out-String
        Write-Host $fetchOut.TrimEnd()
        Add-Content -Path $logFile -Value $fetchOut.TrimEnd() -Encoding UTF8
        if ($LASTEXITCODE -ne 0) {
            Write-Log "FETCH FAILED exit=$LASTEXITCODE (沿用已有快照)"
            Write-Warning "抓取失败，沿用已有快照继续。"
        } else {
            Write-Log "FETCH OK"
        }
    } else {
        Write-Host "== 跳过抓取，使用已有快照 ==" -ForegroundColor DarkGray
        Write-Log "FETCH SKIPPED"
    }

    Write-Host "== 2/2  重算指数并生成网页 ==" -ForegroundColor Cyan
    $buildOut = & $python scripts\build_teci.py 2>&1 | Out-String
    Write-Host $buildOut.TrimEnd()
    Add-Content -Path $logFile -Value $buildOut.TrimEnd() -Encoding UTF8

    if ($LASTEXITCODE -ne 0) {
        Write-Log "BUILD FAILED exit=$LASTEXITCODE"
        throw "指数构建失败，详见 logs/run.log"
    }
    Write-Log "BUILD OK"

    Write-Host ""
    Write-Host "完成。网页位置：" -ForegroundColor Green
    Write-Host "  site\index.html            （需要同目录的 data\teci.js）"
    Write-Host "  site\teci-standalone.html  （单文件，可直接发给别人）"

    Write-Log "=== DONE ==="

    if (-not $NoOpen) {
        Start-Process (Join-Path $root "site\teci-standalone.html")
    }
}
catch {
    Write-Log ("ERROR: " + $_.Exception.Message)
    Write-Host ""
    Write-Host ("失败：" + $_.Exception.Message) -ForegroundColor Red
    Write-Host "日志：" -NoNewline
    Write-Host $logFile -ForegroundColor Yellow
    throw
}
finally {
    Pop-Location
}
