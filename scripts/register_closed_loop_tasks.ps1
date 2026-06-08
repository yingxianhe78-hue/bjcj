param(
    [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$Python = "",
    [switch]$UseRuntimeRoot,
    [string]$RuntimeRoot = "runtime_outputs"
)

$ErrorActionPreference = "Stop"

if (-not $Python) {
    $Python = (Get-Command python).Source
}

function New-ClosedLoopCommand {
    param(
        [string]$Task,
        [string]$TimeLabel = ""
    )

    $runner = Join-Path $ProjectRoot "scripts\run_closed_loop_task.py"
    $parts = @("`"$Python`"", "`"$runner`"", $Task)
    if ($TimeLabel) {
        $parts += "--time-label $TimeLabel"
    }
    if ($UseRuntimeRoot) {
        $parts += "--runtime-root `"$RuntimeRoot`""
    }

    return $parts -join " "
}

function Register-ClosedLoopTask {
    param(
        [string]$Name,
        [string]$Task,
        [string]$At,
        [string]$TimeLabel = "",
    [string]$DaysOfWeek = "MON,TUE,WED,THU,FRI"
)

    $command = New-ClosedLoopCommand -Task $Task -TimeLabel $TimeLabel
    schtasks.exe /Create /F /SC WEEKLY /D $DaysOfWeek /ST $At /TN $Name /TR $command | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to register task: $Name"
    }
    Write-Host "Registered: $Name"
}

Register-ClosedLoopTask -Name "BJCJ_ClosedLoop_0925_MorningWatch" -Task "morning-watch" -At "09:25"
Register-ClosedLoopTask -Name "BJCJ_ClosedLoop_0935_Snapshot" -Task "snapshot" -At "09:35" -TimeLabel "09:35"
Register-ClosedLoopTask -Name "BJCJ_ClosedLoop_1000_Snapshot" -Task "snapshot" -At "10:00" -TimeLabel "10:00"
Register-ClosedLoopTask -Name "BJCJ_ClosedLoop_1030_Snapshot" -Task "snapshot" -At "10:30" -TimeLabel "10:30"
Register-ClosedLoopTask -Name "BJCJ_ClosedLoop_1430_Snapshot" -Task "snapshot" -At "14:30" -TimeLabel "14:30"
Register-ClosedLoopTask -Name "BJCJ_ClosedLoop_1505_DailyReport" -Task "daily" -At "15:05"
Register-ClosedLoopTask -Name "BJCJ_ClosedLoop_1520_WeeklyReport" -Task "weekly" -At "15:20" -DaysOfWeek "FRI"

Write-Host "Closed-loop tasks registered. Project root: $ProjectRoot"
if ($UseRuntimeRoot) {
    Write-Host "Runtime root fallback enabled: $RuntimeRoot"
} else {
    Write-Host "Standard paths enabled: data/ and reports/"
}
