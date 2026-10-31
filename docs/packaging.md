# Windows packaging and target validation

## Developer environment

Build on 64-bit Windows using Python 3.13. The developer needs Python and the packages pinned in `requirements-build.txt`. The recipient of the finished agent executable does not need a Python installation. PyInstaller bundles the interpreter; builds are specific to the operating system and interpreter used. [PyInstaller operating model](https://pyinstaller.org/en/stable/operating-mode.html).

From the repository directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\scripts\build_windows.ps1 -Bundle onedir
.\scripts\build_windows.ps1 -Bundle onefile
```

The build script verifies the pinned tool versions and Python minor version. Use `-Python 'C:\path\to\python.exe'` to select another correctly configured build environment. `-InstallDependencies` installs the pinned build requirements; the default uses the existing environment.

The debugging build is `dist/Task1CodeAgent/Task1CodeAgent.exe`. Distribute that **whole folder**, including `_internal`. The single-file build is `dist/Task1CodeAgent.exe`. Both include the input documents, Tkinter resources, and the supported standard-library worker modules. The chosen options and extra-data/hidden-import mechanisms follow the [PyInstaller usage documentation](https://pyinstaller.org/en/stable/usage.html).

## What the automatic smoke check proves

After each build, the script starts the executable with `--self-test`, both input paths, and a fresh output folder. It checks process exit code and a machine-readable `offline_verified` report with passing tests. This exercises the bundled worker without using `python` from PATH or calling DeepSeek. Build evidence records the executable hash and size in `dist/Task1CodeAgent-<bundle>-build.json`; diagnostic output stays under `build/smoke-*`.

This is a **mocked diagnostic**, not an AI-generated game demonstration. `-SkipSmokeTest` is available for troubleshooting and is recorded as skipped. A Windows developer computer or GitHub Actions runner normally has Python installed; this check alone does not establish clean-target compatibility.

The agent's test/run operations start the same bundled executable in worker mode. Generated projects must use the supported standard-library modules. It is not a general-purpose installed Python distribution and does not install model-suggested dependencies.

## Build the genuinely generated game

A genuine run and reviewed game now exist, with immutable model output and disclosed operator changes. The local game is dist/game/SpaceFractions.exe. To reproduce a reviewed run, retain its complete provenance and passed independent tests, then:

```powershell
.\scripts\build_game.ps1 -RunDirectory '.\runs\run_\<run-id>' -ReviewedSource
```

The exported reviewed project can be rebuilt without a private run folder or API
key. This command also avoids replacing an executable that is currently open:

```powershell
.\scripts\build_game.ps1 -RunDirectory '.\examples\space_fractions' -ReviewedSource -OutputDirectory 'dist\repro-game'
```

The script verifies the pinned build environment, then requires live DeepSeek provenance, a `tests_passed` status, independent-contract evidence, and matching manifest/source hashes. It rejects offline fixtures, changed or unexpected project files (including extra `.pyc` files under `__pycache__`), and failed static validation. Use the agent's bundled runner to preserve the verified project tree; direct source execution may create bytecode files that invalidate this check. `-ReviewedSource` records the developer's decision to package reviewed code; it does not turn generated code into trusted code.

The game output is `dist/game/SpaceFractions.exe`, with separate build evidence. Text resources are bundled; writable questions, credentials, and score data must remain in the per-user application-data location implemented by the generated game. Inspect resource paths in the generated source, then test the actual packaged result. Game packaging needs the developer's pinned Python/PyInstaller environment; the agent does not autonomously supply a compiler toolchain to target PCs.

## Clean Windows acceptance checklist

Use a disposable Windows VM or an already available Windows Sandbox with no Python installation. No Windows feature installation is part of this project. Copy a portable kit containing only the application and verification inputs:

```text
Task1CodeAgent-preview/
  Task1CodeAgent.exe
  inputs/
    Architecture_Documentation.md
    Architecture_View.md
  scripts/
    verify_windows.ps1
```

For a one-folder build, copy the complete `Task1CodeAgent` directory instead of the single root executable. The verifier locates both layouts. Include the README and this packaging guide for the recipient. Do not include an API key, local cost ledger, development environment, raw private screenshots, or previous run folders in the kit.

On the developer machine, this command checks the existing executable under `dist` without creating a clean-machine claim:

```powershell
.\scripts\verify_windows.ps1
```

Inside the copied kit on the clean Windows machine, open PowerShell in the kit folder and run:

```powershell
.\scripts\verify_windows.ps1 -PackageRoot . -ConfirmCleanWindows
```

Supply `-ConfirmCleanWindows` only when the operator actually knows the VM is clean and has no pre-installed Python. It records an **operator assertion**, separate from observed results; the script does not inspect PATH or independently establish installation state. It uses only Windows PowerShell/.NET and the supplied executable, launches a bounded offline diagnostic, verifies worker tests and Tcl/Tk, and records executable/input hashes and Windows version. There is no paid API call or Python command.

Reports go to `%LOCALAPPDATA%\Task1CodeAgent\verification\<verification-id>\verification.json`. Use `-ReportFolder 'C:\Task1 verification reports'` for an explicit output location. The compact `verification.json` excludes local absolute paths. The adjacent `diagnostic` tree retains raw local details; inspect it before sharing. Manual visible GUI checks remain `pending` in the automatic report.

For custom layouts, all paths can be selected explicitly:

```powershell
.\scripts\verify_windows.ps1 -PackageRoot . `
  -Executable '.\Task1CodeAgent\Task1CodeAgent.exe' `
  -ArchitectureFile '.\inputs\Architecture_Documentation.md' `
  -ViewsFile '.\inputs\Architecture_View.md' `
  -ReportFolder 'C:\Task1 verification reports'
```

Record the artifact SHA-256, date, actions, and observed manual results separately from the automatic report. Repeat from a kit location with spaces and non-ASCII characters.

- Double-click the agent as a normal user; check its file selectors, bundled default documents, masked key field, responsive controls, and cancellation.
- Run the portable verification command and inspect its test/run summary. Establish the clean VM's lack of a Python installation from its setup history; an absent `python` command alone does not establish that fact.
- Place copies under a path containing spaces and non-ASCII characters, then repeat input selection, output generation, and diagnostics.
- After separately authorizing a bounded paid call, demonstrate real generation and source review. Preserve usage and provenance; do not repeat a successful paid run for a cleaner recording.
- Review and launch the real generated game through the agent. For the standalone game executable, test intro/skip, menu, keyboard and mouse answers, pause/resume, restart, ending, help, score persistence, admin setup, rejected invalid edits, and saved valid edits.
- Restart both applications and verify the cumulative cost ledger and game data persist. Confirm the API key is absent from output, logs, and game files.

These checks remain pending until actually performed. Do not label a build or mock smoke result as clean-machine evidence. The process limits and path checks are not a security sandbox; use the disposable environment for reviewed live-generated code.

## Continuous integration

`.github/workflows/windows-build.yml` can be started manually with `workflow_dispatch`; it runs offline tests, builds both bundles on Windows, checks the packaged diagnostic, and retains build artifacts. It does not run automatically on push, call DeepSeek, require secrets, upload a video, or create a release. Actions are pinned to the inspected commit SHAs resolved from their current v7 tags: [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python), and [upload-artifact](https://github.com/actions/upload-artifact).


Latest delivery build used `-OutputDirectory dist/current` because an older executable was open. This selects a fresh workspace-local artifact directory without interrupting the active desktop session. Build evidence identifies the actual delivered paths and hashes. The final reviewed game passes 47 checks through the packaged agent runner with System32-only PATH; bundled official model access was also checked read-only. Those are developer-host results, not a clean-machine claim.
