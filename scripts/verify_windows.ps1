[CmdletBinding()]
param(
    [string]$PackageRoot = '',
    [string]$Executable = '',
    [string]$ArchitectureFile = '',
    [string]$ViewsFile = '',
    [string]$ReportFolder = '',
    [ValidateRange(5, 60)]
    [int]$TimeoutSeconds = 60,
    [switch]$ConfirmCleanWindows
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Run this portable verification script on Windows.' }

# This script uses only Windows PowerShell/.NET and the supplied application EXE.
# It neither invokes Python nor infers its installation state from PATH.
if (-not $PackageRoot) { $PackageRoot = Join-Path $PSScriptRoot '..' }
if (-not $ReportFolder) {
    $LocalDataDirectory = [Environment]::GetFolderPath('LocalApplicationData')
    if (-not $LocalDataDirectory) { throw 'LocalAppData is unavailable; specify -ReportFolder explicitly.' }
    $ReportFolder = Join-Path $LocalDataDirectory 'Task1CodeAgent\verification'
}
$ReportFolder = [IO.Path]::GetFullPath($ReportFolder)
$VerificationId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '_' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$RunFolder = Join-Path $ReportFolder $VerificationId
[IO.Directory]::CreateDirectory($RunFolder) | Out-Null
$DiagnosticFolder = Join-Path $RunFolder 'diagnostic'
[IO.Directory]::CreateDirectory($DiagnosticFolder) | Out-Null
$ReportPath = Join-Path $RunFolder 'verification.json'
$Started = [DateTime]::UtcNow
$Elapsed = [Diagnostics.Stopwatch]::StartNew()
$Evidence = [ordered]@{
    schema_version = 1
    verification_id = $VerificationId
    started_utc = $Started.ToString('o')
    completed_utc = $null
    windows_version = [Environment]::OSVersion.VersionString
    operating_system_bitness = if ([Environment]::Is64BitOperatingSystem) { 64 } else { 32 }
    artifact = $null
    inputs = @()
    overall_status = 'failed'
    process_exit_code = $null
    elapsed_seconds = $null
    automated_diagnostic = $null
    clean_windows = [ordered]@{
        operator_asserted = [bool]$ConfirmCleanWindows
        assertion = if ($ConfirmCleanWindows) {
            'Operator asserts this is a clean Windows environment without pre-installed Python.'
        } else { 'No clean-environment assertion was supplied.' }
        independently_established = $false
        python_installation_inspection = 'not performed; PATH is not evidence of installation state'
    }
    manual_visual_validation = 'pending'
    live_generation = 'not performed; offline mock diagnostic only'
    errors = @()
}
$VerificationFailure = $null
$SmokeProcess = $null
try {
    $ResolvedRoot = (Resolve-Path -LiteralPath $PackageRoot).Path
    if (-not $Executable) {
        $Candidates = @(
            (Join-Path $ResolvedRoot 'Task1CodeAgent.exe'),
            (Join-Path $ResolvedRoot 'dist\Task1CodeAgent.exe'),
            (Join-Path $ResolvedRoot 'Task1CodeAgent\Task1CodeAgent.exe'),
            (Join-Path $ResolvedRoot 'dist\Task1CodeAgent\Task1CodeAgent.exe')
        )
        foreach ($Candidate in $Candidates) {
            if (Test-Path -LiteralPath $Candidate -PathType Leaf) { $Executable = $Candidate; break }
        }
    }
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw 'The supplied application executable is missing; specify -Executable.'
    }
    if (-not $ArchitectureFile) { $ArchitectureFile = Join-Path $ResolvedRoot 'inputs\Architecture_Documentation.md' }
    if (-not $ViewsFile) { $ViewsFile = Join-Path $ResolvedRoot 'inputs\Architecture_View.md' }
    if (-not (Test-Path -LiteralPath $ArchitectureFile -PathType Leaf)) { throw 'Architecture documentation input is missing.' }
    if (-not (Test-Path -LiteralPath $ViewsFile -PathType Leaf)) { throw 'Architecture views input is missing.' }
    $ResolvedExecutable = (Resolve-Path -LiteralPath $Executable).Path
    $ResolvedArchitecture = (Resolve-Path -LiteralPath $ArchitectureFile).Path
    $ResolvedViews = (Resolve-Path -LiteralPath $ViewsFile).Path
    $ExecutableItem = Get-Item -LiteralPath $ResolvedExecutable
    $Evidence.artifact = [ordered]@{
        filename = $ExecutableItem.Name
        bytes = $ExecutableItem.Length
        sha256 = (Get-FileHash -LiteralPath $ResolvedExecutable -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    foreach ($InputFile in @($ResolvedArchitecture, $ResolvedViews)) {
        $InputItem = Get-Item -LiteralPath $InputFile
        $Evidence.inputs += [ordered]@{
            filename = $InputItem.Name
            bytes = $InputItem.Length
            sha256 = (Get-FileHash -LiteralPath $InputFile -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    # Windows filenames cannot contain quotes. All three paths are explicit args;
    # there is no shell command string, model command, or dependency installation.
    $StartInfo = New-Object Diagnostics.ProcessStartInfo
    $StartInfo.FileName = $ResolvedExecutable
    $StartInfo.Arguments = '--self-test "' + $ResolvedArchitecture + '" "' + $ResolvedViews + '" "' + $DiagnosticFolder + '"'
    $StartInfo.WorkingDirectory = $RunFolder
    $StartInfo.UseShellExecute = $false
    $StartInfo.CreateNoWindow = $true
    foreach ($SecretVariable in @('DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY')) {
        $StartInfo.EnvironmentVariables.Remove($SecretVariable)
    }
    $SmokeProcess = [Diagnostics.Process]::Start($StartInfo)
    if (-not $SmokeProcess.WaitForExit($TimeoutSeconds * 1000)) {
        $SmokeProcess.Kill()
        throw 'The packaged offline diagnostic timed out.'
    }
    $Evidence.process_exit_code = $SmokeProcess.ExitCode
    if ($SmokeProcess.ExitCode -ne 0) { throw 'The packaged offline diagnostic returned a failure exit code.' }
    $DiagnosticReport = Join-Path $DiagnosticFolder 'self_test_result.json'
    if (-not (Test-Path -LiteralPath $DiagnosticReport -PathType Leaf)) { throw 'The packaged offline diagnostic returned no JSON report.' }
    if ((Get-Item -LiteralPath $DiagnosticReport).Length -gt 200000) { throw 'The diagnostic JSON report exceeds the 200 KB limit.' }
    $Result = Get-Content -LiteralPath $DiagnosticReport -Raw -Encoding UTF8 | ConvertFrom-Json
    $Evidence.automated_diagnostic = [ordered]@{
        mode = [string]$Result.mode
        status = [string]$Result.status
        tkinter_runtime = [string]$Result.tkinter_runtime
        tests_ok = [bool]$Result.validation.ok
        tests_run = [int]$Result.validation.tests_run
    }
    if ($Result.mode -ne 'offline_mock' -or $Result.status -ne 'offline_verified' -or
        $Result.tkinter_runtime -ne 'passed' -or $Result.validation.ok -ne $true -or
        $Result.validation.tests_run -lt 1) {
        throw 'The offline mock, bundled tests, and Tcl/Tk runtime did not all pass.'
    }
    $Evidence.overall_status = 'offline_checks_passed'
}
catch {
    # Keep the portable summary small and free of local paths and raw tracebacks.
    $KnownMessages = @(
        'The supplied application executable is missing; specify -Executable.',
        'Architecture documentation input is missing.',
        'Architecture views input is missing.',
        'The packaged offline diagnostic timed out.',
        'The packaged offline diagnostic returned a failure exit code.',
        'The packaged offline diagnostic returned no JSON report.',
        'The diagnostic JSON report exceeds the 200 KB limit.',
        'The offline mock, bundled tests, and Tcl/Tk runtime did not all pass.'
    )
    $FailureMessage = $_.Exception.Message
    if ($FailureMessage -notin $KnownMessages) { $FailureMessage = 'Verification could not complete; check the supplied paths, permissions, and local diagnostic files.' }
    $Evidence.errors = @($FailureMessage)
    $VerificationFailure = $FailureMessage
}
finally {
    $Elapsed.Stop()
    $Evidence.completed_utc = [DateTime]::UtcNow.ToString('o')
    $Evidence.elapsed_seconds = [Math]::Round($Elapsed.Elapsed.TotalSeconds, 3)
    $Evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ReportPath -Encoding UTF8
    if ($SmokeProcess) { $SmokeProcess.Dispose() }
}
Write-Host "Verification report: $ReportPath"
Write-Host "Offline checks: $($Evidence.overall_status). Manual visual validation: pending."
if ($ConfirmCleanWindows) {
    Write-Host 'Clean Windows was asserted by the operator; this script did not establish that assertion independently.'
} else { Write-Host 'Clean Windows was not asserted or established.' }
if ($VerificationFailure) { throw $VerificationFailure }
