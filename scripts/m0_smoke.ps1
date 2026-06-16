# M.0 smoke harness — load + forward + divergence check.
#
# Reuses tools/sp_daemon/target/release/probe.exe (engine repo, READ-ONLY) to
# drive sp_model_load + sp_session_create + sp_prefill_chunk + sp_decode_step
# against the M.0 Memory and Executive models. Probe prints logits[0..3] for
# both prefill (3 tokens) and decode (1 token). M.0 uses those to confirm:
#
#   T_MEMO_M0_LOADS  — sp_model_load returns SP_OK, arch query yields valid dims.
#   T_MEMO_M0_FORWARDS — prefill + decode succeed with non-NaN logits.
#   T_MEMO_M0_DISTINCT_FROM_EXECUTIVE — Memory and Executive logits diverge.
#
# Stable cache paths assumed (M.0 closure note documents these as the canonical
# M.0 location):
#   D:\F\shannon-prime-repos\models\qwen25-coder-0.5b-memory.sp-model      (Memory)
#   D:\F\shannon-prime-repos\models\qwen25-coder-0.5b-memory.sp-tokenizer
# and the existing Executive artifact:
#   D:\F\shannon-prime-repos\shannon-prime-system-engine\build-cpu\tests\qwen3_rt.sp-model

$ErrorActionPreference = 'Stop'

$memModel = 'D:\F\shannon-prime-repos\models\qwen25-coder-0.5b-memory.sp-model'
$memTok   = 'D:\F\shannon-prime-repos\models\qwen25-coder-0.5b-memory.sp-tokenizer'
$exeModel = 'D:\F\shannon-prime-repos\shannon-prime-system-engine\build-cpu\tests\qwen3_rt.sp-model'
$exeTok   = 'D:\F\shannon-prime-repos\shannon-prime-system-engine\build-cpu\tests\qwen3_rt.sp-tokenizer'
$probe    = 'D:\F\shannon-prime-repos\shannon-prime-system-engine\tools\sp_daemon\target\release\probe.exe'

foreach ($p in @($memModel, $memTok, $exeModel, $exeTok, $probe)) {
    if (-not (Test-Path $p)) { Write-Error "MISSING: $p"; exit 2 }
}

function Run-Probe([string]$name, [string]$model, [string]$tok) {
    $stdoutFile = Join-Path $env:TEMP "m0_probe_${name}.out"
    $stderrFile = Join-Path $env:TEMP "m0_probe_${name}.err"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $proc = Start-Process -FilePath $probe -ArgumentList $model, $tok -NoNewWindow -PassThru `
        -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile
    $peakKB = 0
    while (-not $proc.HasExited) {
        try {
            $proc.Refresh()
            $ws = $proc.WorkingSet64
            if ($ws / 1024 -gt $peakKB) { $peakKB = [math]::Round($ws / 1024) }
        } catch {}
        Start-Sleep -Milliseconds 30
    }
    $sw.Stop()
    $proc.WaitForExit()
    try {
        $peakProcKB = [math]::Round($proc.PeakWorkingSet64 / 1024)
        if ($peakProcKB -gt $peakKB) { $peakKB = $peakProcKB }
    } catch {}
    $out = Get-Content $stdoutFile -Raw
    $err = Get-Content $stderrFile -Raw

    $result = [PSCustomObject]@{
        Name        = $name
        ExitCode    = $proc.ExitCode
        WallMs      = $sw.ElapsedMilliseconds
        PeakMB      = [math]::Round($peakKB / 1024, 1)
        Stdout      = $out
        Stderr      = $err
        ArchVocab   = $null
        ArchLayers  = $null
        ArchHidden  = $null
        PrefillL0   = $null
        PrefillL1   = $null
        PrefillL2   = $null
        DecodeL0    = $null
        DecodeL1    = $null
        DecodeL2    = $null
        ProbeStatus = ''
    }
    if ($out -match 'arch:\s*vocab=(\d+)\s*n_layers=(\d+)\s*hidden=(\d+)') {
        $result.ArchVocab  = [int]$Matches[1]
        $result.ArchLayers = [int]$Matches[2]
        $result.ArchHidden = [int]$Matches[3]
    }
    if ($out -match 'prefill\(3\) OK — logits\[0\.\.3\] = \[([-\d.e+]+),\s*([-\d.e+]+),\s*([-\d.e+]+)\]') {
        $result.PrefillL0 = [double]$Matches[1]
        $result.PrefillL1 = [double]$Matches[2]
        $result.PrefillL2 = [double]$Matches[3]
    }
    if ($out -match 'decode\(1\) OK — position=4, logits\[0\.\.3\] = \[([-\d.e+]+),\s*([-\d.e+]+),\s*([-\d.e+]+)\]') {
        $result.DecodeL0 = [double]$Matches[1]
        $result.DecodeL1 = [double]$Matches[2]
        $result.DecodeL2 = [double]$Matches[3]
    }
    if ($out -match 'PROBE PASS') { $result.ProbeStatus = 'PASS' } else { $result.ProbeStatus = 'FAIL' }
    return $result
}

Write-Host "=== M.0 SMOKE: probe Memory + Executive ==="
$mem = Run-Probe -name 'memory'    -model $memModel -tok $memTok
$exe = Run-Probe -name 'executive' -model $exeModel -tok $exeTok

Write-Host ""
Write-Host "Memory   : exit=$($mem.ExitCode)  wall=$($mem.WallMs)ms  peakRSS=$($mem.PeakMB)MB  status=$($mem.ProbeStatus)"
Write-Host "           arch vocab=$($mem.ArchVocab) layers=$($mem.ArchLayers) hidden=$($mem.ArchHidden)"
Write-Host "           prefill[0..3]=[$($mem.PrefillL0), $($mem.PrefillL1), $($mem.PrefillL2)]"
Write-Host "           decode[0..3] =[$($mem.DecodeL0), $($mem.DecodeL1), $($mem.DecodeL2)]"
Write-Host ""
Write-Host "Executive: exit=$($exe.ExitCode)  wall=$($exe.WallMs)ms  peakRSS=$($exe.PeakMB)MB  status=$($exe.ProbeStatus)"
Write-Host "           arch vocab=$($exe.ArchVocab) layers=$($exe.ArchLayers) hidden=$($exe.ArchHidden)"
Write-Host "           prefill[0..3]=[$($exe.PrefillL0), $($exe.PrefillL1), $($exe.PrefillL2)]"
Write-Host "           decode[0..3] =[$($exe.DecodeL0), $($exe.DecodeL1), $($exe.DecodeL2)]"
Write-Host ""

# T_MEMO_M0_LOADS
$loadsPass = $mem.ProbeStatus -eq 'PASS' -and $mem.ArchVocab -gt 0
Write-Host ("T_MEMO_M0_LOADS:                  " + $(if($loadsPass){'PASS'}else{'FAIL'}))

# T_MEMO_M0_FORWARDS — non-null logits, non-NaN
$forwardsPass = $mem.PrefillL0 -ne $null -and $mem.DecodeL0 -ne $null `
              -and -not [double]::IsNaN($mem.PrefillL0) -and -not [double]::IsNaN($mem.DecodeL0) `
              -and $mem.WallMs -lt 5000
Write-Host ("T_MEMO_M0_FORWARDS:                " + $(if($forwardsPass){'PASS'}else{'FAIL'}))

# T_MEMO_M0_DISTINCT_FROM_EXECUTIVE — any logit differs
$pairs = @(
    @($mem.PrefillL0, $exe.PrefillL0),
    @($mem.PrefillL1, $exe.PrefillL1),
    @($mem.PrefillL2, $exe.PrefillL2),
    @($mem.DecodeL0,  $exe.DecodeL0),
    @($mem.DecodeL1,  $exe.DecodeL1),
    @($mem.DecodeL2,  $exe.DecodeL2)
)
$divergentPositions = 0
foreach ($p in $pairs) { if ($p[0] -ne $p[1]) { $divergentPositions++ } }
$distinctPass = $divergentPositions -ge 1
Write-Host ("T_MEMO_M0_DISTINCT_FROM_EXECUTIVE: " + $(if($distinctPass){"PASS ($divergentPositions/6 positions diverge)"}else{'FAIL'}))

if (-not ($loadsPass -and $forwardsPass -and $distinctPass)) { exit 1 }
Write-Host ""
Write-Host "M.0 smoke: ALL 3 RUNTIME GATES PASS"
exit 0
