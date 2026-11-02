[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunDirectory,
    [string]$Python = '',
    [string]$OutputDirectory = '',
    [switch]$ReviewedSource
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Build this Windows executable on Windows.' }
if (-not $ReviewedSource) { throw 'Review the generated source, then supply -ReviewedSource to package it.' }
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not $Python) { $Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'The pinned developer build environment is missing.' }
$BuildPython = (Resolve-Path -LiteralPath $Python).Path
$RunPath = (Resolve-Path -LiteralPath $RunDirectory).Path
$EvidenceDirectory = if (Test-Path -LiteralPath (Join-Path $RunPath 'run_summary.json')) {
    $RunPath
} elseif (Test-Path -LiteralPath (Join-Path $RunPath 'provenance\run_summary.json')) {
    Join-Path $RunPath 'provenance'
} else { throw 'A real run summary or exported provenance directory is required.' }

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

# Read evidence and source as data. Do not import or execute the generated game here.
$CheckProvenance = @'
from pathlib import Path
import hashlib, json, sys
repository, run, evidence = map(Path, sys.argv[1:])
sys.path.insert(0, str(repository / 'src'))
from code_agent.workspace_tools import parse_manifest, ensure_regular_tree
from code_agent.validator import static_validate
ensure_regular_tree(run)
summary = json.loads((evidence / 'run_summary.json').read_text(encoding='utf-8'))
if summary.get('mode') != 'live_deepseek' or summary.get('model') != 'deepseek-v4-pro':
    raise SystemExit('Only genuine live DeepSeek generation may be packaged as the submission game.')
if summary.get('status') != 'tests_passed' or not summary.get('requests'):
    raise SystemExit('A live run with passed tests and recorded requests is required.')
validation = summary.get('validation') or {}
if validation.get('ok') is not True or validation.get('independent_contract') is not True:
    raise SystemExit('Independent game contract tests must pass before packaging.')
manifest = parse_manifest((evidence / 'manifest.json').read_text(encoding='utf-8'))
recorded = {item['path']: item['sha256'] for item in summary['files']}
expected = {item['path']: hashlib.sha256(item['content'].encode('utf-8')).hexdigest()
            for item in manifest['files']}
if recorded != expected:
    raise SystemExit('Run summary hashes do not match the generated manifest.')
project = run / 'project'
actual = {p.relative_to(project).as_posix() for p in project.rglob('*') if p.is_file()}
if actual != set(expected):
    raise SystemExit('Unexpected or missing project files; use an unchanged verified run.')
for name, digest in expected.items():
    if hashlib.sha256((project / name).read_bytes()).hexdigest() != digest:
        raise SystemExit('Generated files changed after validation; review and validate again.')
check = static_validate(project)
if not check['ok']:
    raise SystemExit('Static validation failed: ' + json.dumps(check['errors']))
print(str(project.resolve()))
'@
$GeneratedProject = & $BuildPython -c $CheckProvenance $ProjectRoot $RunPath $EvidenceDirectory
if ($LASTEXITCODE -ne 0) { throw 'Game provenance check failed; no executable was built.' }
$GeneratedProject = [string]$GeneratedProject

$Distribution = if ($OutputDirectory) {
    [IO.Path]::GetFullPath((Join-Path $ProjectRoot $OutputDirectory))
} else { Join-Path $ProjectRoot 'dist\game' }
if (-not $Distribution.StartsWith($ProjectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Build output must be inside the project workspace.'
}
$WorkDirectory = Join-Path $ProjectRoot 'build\game'
$SpecDirectory = Join-Path $ProjectRoot 'build\game-spec'
New-Item -ItemType Directory -Path $Distribution, $WorkDirectory, $SpecDirectory -Force | Out-Null
$BuildArguments = @(
    '-m', 'PyInstaller', '--noconfirm', '--noupx', '--windowed', '--onefile',
    '--name', 'SpaceFractions', '--paths', $GeneratedProject,
    '--distpath', $Distribution, '--workpath', $WorkDirectory, '--specpath', $SpecDirectory,
    '--hidden-import', 'tkinter.ttk', '--hidden-import', 'tkinter.messagebox',
    '--hidden-import', 'tkinter.simpledialog', '--hidden-import', 'tkinter.font',
    '--hidden-import', 'sqlite3', '--hidden-import', 'fractions', '--hidden-import', 'secrets'
)
# Include approved text resources at their original relative paths; runtime DBs belong in AppData.
$Resources = Get-ChildItem -LiteralPath $GeneratedProject -Recurse -File | Where-Object {
    $_.Extension -in @('.json', '.csv', '.txt', '.sql') -and $_.Name -ne 'requirements.txt'
}
foreach ($Resource in $Resources) {
    $RelativeDirectory = $Resource.DirectoryName.Substring($GeneratedProject.Length).TrimStart('\')
    if (-not $RelativeDirectory) { $RelativeDirectory = '.' }
    $BuildArguments += @('--add-data', ($Resource.FullName + ':' + $RelativeDirectory))
}
$BuildArguments += (Join-Path $GeneratedProject 'main.py')
Push-Location -LiteralPath $GeneratedProject
try {
    & $BuildPython @BuildArguments
    if ($LASTEXITCODE -ne 0) { throw 'Generated game packaging failed.' }
}
finally { Pop-Location }
$Executable = Join-Path $Distribution 'SpaceFractions.exe'
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw 'Expected game executable is missing.' }
$VerifiedSummary = Get-Content -LiteralPath (Join-Path $EvidenceDirectory 'run_summary.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$ManualAdjustments = @(if ($VerifiedSummary.PSObject.Properties.Name -contains 'manual_adjustments') { $VerifiedSummary.manual_adjustments })
$Evidence = [ordered]@{
    created_utc = [DateTime]::UtcNow.ToString('o')
    source_run_id = $VerifiedSummary.run_id
    source_model = $VerifiedSummary.model
    source_origin = if ($ManualAdjustments.Count -gt 0) { 'DeepSeek generation plus disclosed operator adjustments' } else { 'DeepSeek generation' }
    manual_adjustments = $ManualAdjustments
    artifact = $Executable.Substring($ProjectRoot.Length + 1)
    sha256 = (Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash.ToLowerInvariant()
    pyinstaller = '6.22.3'
    clean_machine_validation = 'pending'
    manual_playthrough = 'pending'
}
$Evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Distribution 'build_evidence.json') -Encoding UTF8
Write-Host "Built $Executable. Test the packaged game manually and on clean Windows before submission."
