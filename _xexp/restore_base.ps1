# X 实验归档恢复脚本（可复现性保障）
# 用途：从归档状态重建冻结基线副本 base/（base 在父仓库中以 gitlink 记录，内容需从此脚本重建）
# 前置：zixun4 源码库存在（G:\workspace\zixun4），其 git 历史含冻结基线 27afc5e
# 运行：pwsh -File restore_base.ps1
$ErrorActionPreference = "Stop"
$git = "C:\Program Files\Git\cmd\git.exe"
$srcRepo = "G:\workspace\zixun4"
$baseDir = Join-Path $PSScriptRoot "base"
$tarFile = Join-Path $PSScriptRoot "base.tar"
$venvPy = "G:\workspace\.venv-zixun4\Scripts\python.exe"

Write-Host "=== 1. 校验 zixun4 冻结基线存在 ==="
& $git -C $srcRepo cat-file -e 27afc5e 2>$null
if ($LASTEXITCODE -ne 0) { throw "冻结基线 27afc5e 不存在于 zixun4 仓库" }
Write-Host "冻结基线 27afc5e OK"

Write-Host "=== 2. 归档冻结基线 ==="
if (Test-Path $baseDir) { Remove-Item $baseDir -Recurse -Force }
New-Item -ItemType Directory -Path $baseDir -Force | Out-Null
& $git -C $srcRepo archive --format=tar -o $tarFile 27afc5e
tar -xf $tarFile -C $baseDir
Write-Host "base/ 已从 27afc5e 重建"

Write-Host "=== 3. base 初始化为 git 仓库（供引擎 apply/回滚）==="
Push-Location $baseDir
& $git init | Out-Null
& $git config user.name "xexp"; & $git config user.email "xexp@local"
& $git add -A | Out-Null
& $git commit -m "frozen baseline 27afc5e clean copy" | Out-Null
Pop-Location
Write-Host "base git 仓库已初始化"

Write-Host "=== 4. 复现基线测试（应 273 passed）==="
Push-Location $baseDir
$out = & $venvPy -m pytest -q --ignore=tests/eval/test_validator_framework.py 2>&1 | Select-Object -Last 1
Pop-Location
Write-Host $out
Write-Host "=== 恢复完成 ==="
