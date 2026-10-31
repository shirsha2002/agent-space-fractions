[CmdletBinding()]
param(
    [ValidateSet('onefile', 'onedir')]
    [string]$Bundle = 'onefile',
    [string]$Python = '',
    [string]$OutputDirectory = '',
    [switch]$InstallDependencies,
    [switch]$SkipSmokeTest
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Build this Windows executable on Windows.' }
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not $Python) { $Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Create .venv with Python 3.13 and install requirements-build.txt first; see docs/packaging.md.'
}
$BuildPython = (Resolve-Path -LiteralPath $Python).Path
$Distribution = if ($OutputDirectory) {
    [IO.Path]::GetFullPath((Join-Path $ProjectRoot $OutputDirectory))
} else { Join-Path $ProjectRoot 'dist' }
if (-not $Distribution.StartsWith($ProjectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Build output must be inside the project workspace.'
}
$WorkDirectory = Join-Path $ProjectRoot "build\agent-$Bundle"
$SpecDirectory = Join-Path $ProjectRoot "build\spec-$Bundle"
$InputDirectory = Join-Path $ProjectRoot 'inputs'
New-Item -ItemType Directory -Path $Distribution, $WorkDirectory, $SpecDirectory -Force | Out-Null

Push-Location -LiteralPath $ProjectRoot
try {
    if ($InstallDependencies) {
        & $BuildPython -m pip install -r (Join-Path $ProjectRoot 'requirements-build.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }
    }
    $CheckVersions = @'
from importlib.metadata import version
from pathlib import Path
import sys
for line in Path(sys.argv[1]).read_text(encoding='utf-8').splitlines():
    if line.strip() and not line.lstrip().startswith('#'):
        package, expected = line.strip().split('==')
        actual = version(package)
        if actual != expected:
            raise SystemExit(f'{package}: expected {expected}, installed {actual}')
if sys.version_info[:2] != (3, 13):
    raise SystemExit('Use Python 3.13 for the reproducible build.')
'@
    & $BuildPython -c $CheckVersions (Join-Path $ProjectRoot 'requirements-build.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Pinned build environment check failed.' }

    $BuildArguments = @(
        '-m', 'PyInstaller', '--noconfirm', '--noupx', '--windowed', "--$Bundle",
        '--name', 'Task1CodeAgent', '--paths', (Join-Path $ProjectRoot 'src'),
        '--add-data', "${InputDirectory}:inputs",
        '--distpath', $Distribution, '--workpath', $WorkDirectory, '--specpath', $SpecDirectory
    )
    # Generated modules are loaded dynamically; bundle the supported stdlib surface.
    $HiddenImports = @(
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.simpledialog',
        'tkinter.filedialog', 'tkinter.font', 'sqlite3', 'fractions', 'decimal',
        'secrets', 'dataclasses', 'hashlib', 'datetime', 'math', 'random',
        'unittest', 'unittest.mock', 'unittest.loader', 'unittest.runner',
        'unittest.suite', 'unittest.case', 'json', 'statistics', 'collections',
        'typing', 'pathlib'
    )
    foreach ($Module in $HiddenImports) { $BuildArguments += @('--hidden-import', $Module) }
    $BuildArguments += (Join-Path $ProjectRoot 'launcher.py')
    & $BuildPython @BuildArguments
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }

    $Executable = if ($Bundle -eq 'onefile') {
        Join-Path $Distribution 'Task1CodeAgent.exe'
    } else { Join-Path $Distribution 'Task1CodeAgent\Task1CodeAgent.exe' }
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw 'Expected executable is missing.' }
    $SmokeStatus = 'skipped'
    $SmokeRelativePath = $null
    if (-not $SkipSmokeTest) {
        $SmokeDirectory = Join-Path $ProjectRoot ("build\smoke-$Bundle-" + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $SmokeDirectory | Out-Null
        $SmokeArguments = @(
            '--self-test',
            ('"' + (Join-Path $InputDirectory 'Architecture_Documentation.md') + '"'),
            ('"' + (Join-Path $InputDirectory 'Architecture_View.md') + '"'),
            ('"' + $SmokeDirectory + '"')
        )
        $SmokeProcess = Start-Process -FilePath $Executable -ArgumentList $SmokeArguments -PassThru -WindowStyle Hidden
        if (-not $SmokeProcess.WaitForExit(60000)) {
            $SmokeProcess.Kill()
            throw 'Packaged offline smoke test exceeded 60 seconds.'
        }
        if ($SmokeProcess.ExitCode -ne 0) { throw "Packaged smoke test exited with code $($SmokeProcess.ExitCode)." }
        $SmokeReport = Join-Path $SmokeDirectory 'self_test_result.json'
        if (-not (Test-Path -LiteralPath $SmokeReport -PathType Leaf)) { throw 'Packaged smoke report is missing.' }
        $SmokeResult = Get-Content -LiteralPath $SmokeReport -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($SmokeResult.status -ne 'offline_verified' -or $SmokeResult.mode -ne 'offline_mock' -or
            $SmokeResult.validation.ok -ne $true -or $SmokeResult.validation.tests_run -lt 1) {
            throw 'Packaged offline diagnostic did not pass.'
        }
        $SmokeStatus = 'offline_verified'
        $SmokeRelativePath = $SmokeReport.Substring($ProjectRoot.Length + 1)
    }
    $BuildEvidence = [ordered]@{
        created_utc = [DateTime]::UtcNow.ToString('o')
        artifact = $Executable.Substring($ProjectRoot.Length + 1)
        bundle = $Bundle
        sha256 = (Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash.ToLowerInvariant()
        bytes = (Get-Item -LiteralPath $Executable).Length
        pyinstaller = '6.22.3'
        smoke_status = $SmokeStatus
        smoke_report = $SmokeRelativePath
        clean_machine_validation = 'pending'
        live_generation = 'not tested by this build'
    }
    $EvidencePath = Join-Path $Distribution "Task1CodeAgent-$Bundle-build.json"
    $BuildEvidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8
    Write-Host "Built $Executable"
    Write-Host "Offline smoke: $SmokeStatus. Clean Windows validation remains separate."
}
finally { Pop-Location }
