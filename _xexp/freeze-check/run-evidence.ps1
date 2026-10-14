# 记录 freeze-check v2 本轮运行证据（日志 + 哈希）。
# 说明：受限沙箱禁止创建管道，故不使用 PowerShell 管道捕获子进程输出，
#       改用 Start-Process 的文件重定向（本机已实测可用）。

$ErrorActionPreference = 'Continue'
$dir = 'G:\ds-h\_xexp\freeze-check'

function Invoke-Captured {
    param([string[]]$PyArgs, [string]$Out, [string]$Err)
    $p = Start-Process -FilePath 'python' -ArgumentList $PyArgs -NoNewWindow -PassThru -Wait `
        -RedirectStandardOutput $Out -RedirectStandardError $Err
    $code = $p.ExitCode
    $oLen = (Get-Item $Out).Length
    $eLen = (Get-Item $Err).Length
    return [pscustomobject]@{ rc = $code; out = $oLen; err = $eLen }
}

$runs = @(
    @{ Name = 'py_compile'; Args = @('-m','py_compile', (Join-Path $dir 'freeze_check_v2.py'), (Join-Path $dir 'selftest_v2.py'));
       Out = (Join-Path $dir 'pycompile-out.txt'); Err = (Join-Path $dir 'pycompile-err.txt') },
    @{ Name = 'selftest_v2'; Args = @((Join-Path $dir 'selftest_v2.py'));
       Out = (Join-Path $dir 'selftest-v2-out.txt'); Err = (Join-Path $dir 'selftest-v2-err.txt') },
    @{ Name = 'freeze_check_v2'; Args = @((Join-Path $dir 'freeze_check_v2.py'),'--manifest','v6');
       Out = (Join-Path $dir 'freeze-check-v2-out.txt'); Err = (Join-Path $dir 'freeze-check-v2-err.txt') },
    @{ Name = 'verify_registry'; Args = @((Join-Path $dir '..\risk-registry\verify_registry.py'));
       Out = (Join-Path $dir 'registry-verify-out.txt'); Err = (Join-Path $dir 'registry-verify-err.txt') },
    @{ Name = 'selftest_registry_v3'; Args = @((Join-Path $dir '..\risk-registry\selftest_registry_v3.py'));
       Out = (Join-Path $dir 'selftest-registry-out.txt'); Err = (Join-Path $dir 'selftest-registry-err.txt') }
)

foreach ($r in $runs) {
    Start-Process -FilePath 'python' -ArgumentList $r.Args -NoNewWindow -Wait `
        -RedirectStandardOutput $r.Out -RedirectStandardError $r.Err | Out-Null
    $code = $LASTEXITCODE
    $oLen = (Get-Item $r.Out).Length
    $eLen = (Get-Item $r.Err).Length
    "RESULT name={0} rc={1} out_bytes={2} err_bytes={3}" -f $r.Name, $code, $oLen, $eLen
}

# 单独复现 v1 的 GBK 编码崩溃（强制 PYTHONIOENCODING=gbk）
$env:PYTHONIOENCODING = 'gbk'
$v1 = Invoke-Captured -PyArgs @((Join-Path $dir 'freeze_check.py')) `
    -Out (Join-Path $dir 'v1-repro-out.txt') -Err (Join-Path $dir 'v1-repro-err.txt')
"RESULT name=v1_gbk_repro rc={0} out_bytes={1} err_bytes={2}" -f $v1.rc, $v1.out, $v1.err
Remove-Item Env:PYTHONIOENCODING
