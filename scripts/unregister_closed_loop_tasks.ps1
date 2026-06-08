$ErrorActionPreference = "Stop"

$taskNames = @(
    "BJCJ_ClosedLoop_0925_MorningWatch",
    "BJCJ_ClosedLoop_0935_Snapshot",
    "BJCJ_ClosedLoop_1000_Snapshot",
    "BJCJ_ClosedLoop_1030_Snapshot",
    "BJCJ_ClosedLoop_1430_Snapshot",
    "BJCJ_ClosedLoop_1505_DailyReport",
    "BJCJ_ClosedLoop_1520_WeeklyReport"
)

foreach ($taskName in $taskNames) {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "Unregistered: $taskName"
    } else {
        Write-Host "Not found: $taskName"
    }
}
