# Task 1 · Windows Desktop Code Agent

A small Windows desktop agent that reads architecture documentation and UML descriptions, requests a complete source project from the official DeepSeek API, checks the result, and supports at most two repair rounds. The intended generated application is **Space Fractions**, a desktop fraction-learning game.

**Current delivery status:** a genuine official `deepseek-v4-pro` run produced the game source. The run used one generation plus two bounded model repairs. Its model-only final baseline had one incorrect test vector; disclosed operator fixes complete the local authorization and UI edge cases, and a later visual-only revision adds the animated space interface. The reviewed game passes **47 checks**, and the agent suite passes **56 tests**. Standalone Windows agent and game executables are built locally. The conservative peak-rate API estimate is **USD 0.21462452**, across three paid calls; it is not a provider invoice. See [the real output and immutable provenance](examples/space_fractions/) and [delivery status](docs/delivery_status.md).

**Remaining submission gates:** manual visual/clean-Windows verification, an authentic YouTube demonstration, sharing the public repository link, and executable attachment/upload. Desktop automation was unavailable; internal Tk callback tests do not establish visual appearance. No additional paid calls are needed to play the built game.

The original task explicitly requires the agent as a Windows executable without pre-installed Python. The email requires a desktop generated game and token cost within USD 1. The supplied web/cloud architecture conflicts with the desktop direction, so the modular local-desktop adaptation remains provisional. See [clarifications](docs/clarifications.md) and [requirements traceability](docs/requirements_traceability.md).

## Run the Windows application

Open `dist/current/Task1CodeAgent.exe` for the latest agent, or `dist/game/SpaceFractions.exe` to play the reviewed game. The final local submission ZIP places both executables at its root. The packaged application contains its Python runtime, Tkinter GUI, original architecture inputs, and a worker for checking and launching supported generated projects. End users do not need Python on PATH. A clean machine without Python remains a separate verification step; a successful developer-machine launch does not prove that check.

The GUI opens in **Offline pipeline check** mode:

1. Confirm both Markdown inputs and choose an output parent folder. Each run gets a new directory.
2. Select **Run offline check**. The diagnostic deliberately starts with a syntax error, exercises repair through mocked responses, then runs a diagnostic test. It makes no API call and incurs no API token charge.
3. Select **Open run** to inspect the evidence and **Launch diagnostic** to show the clearly labelled diagnostic window.

For genuine generation, select **Live DeepSeek generation**, enter your key in the masked session-only field and use **Check model**. That button queries the official model listing; it does not request a chat completion. A ChatGPT subscription is unrelated to DeepSeek API credit. Obtain access and, if necessary, fund the official DeepSeek API account when the local implementation is ready for the bounded live demonstration; never paste a key into chat or commit it.

Before starting a live request, select the paid-call authorization checkbox. The required model is fixed to `deepseek-v4-pro` at `https://api.deepseek.com/chat/completions`; the app does not silently substitute another model. Output is capped at 16,000 tokens by default and repairs at two, with lower limits available.

After generation, the app stops at **Review required**. Open the run, review the generated source, select the review checkbox, then choose **Validate & repair reviewed source**. A repaired project requires another source review before execution. Successful tests enable **Launch game**. Runtime test success does not replace manual checks of the UI, persisted scores or administrator editing.

**Cancel** requests a stop. An in-flight network request may finish or reach its bounded timeout before stopping; received usage is still recorded. Closing during work requests cancellation and waits for accounting rather than abandoning an unknown paid request.

## Developer setup

Development and packaging use Windows and Python 3.13 with Tkinter. Runtime application dependencies are standard library only. Build dependencies are pinned in `requirements-build.txt`.

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe launcher.py
```

The key may alternatively be provided through a locally configured `DEEPSEEK_API_KEY` environment variable. `.env.example` is only a placeholder reference: the app does not automatically load `.env` files. The GUI does not save the entered key. Keys are removed from the environment passed to generated-code workers.

Run the offline vertical slice without opening the GUI:

```powershell
.\.venv\Scripts\python.exe launcher.py --self-test inputs\Architecture_Documentation.md inputs\Architecture_View.md runs\offline-evidence
```

This writes `self_test_result.json` and a fresh mocked run beneath the selected output. It proves the offline path only. It deliberately skips the independent Space Fractions contract because the diagnostic is not a game.

Run the agent's unit and integration tests without paid API calls:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Build both Windows bundles:

```powershell
.\scripts\build_windows.ps1 -Bundle onedir
.\scripts\build_windows.ps1 -Bundle onefile
```

The script checks pinned versions and runs a packaged offline smoke test. Build on Windows; PyInstaller is not a cross-compiler. The generated game's developer packaging is a separate step and requires a genuine reviewed, tested live run. See [packaging instructions](docs/packaging.md) and the [submission checklist](docs/submission.md).

## Generation and validation

The agent performs input loading → evidence-linked normalization → official JSON request → manifest validation → fresh-directory materialization → static checks → reviewed execution → bounded repair → summary.

- Both original UTF-8 Markdown files are retained in the model context with byte-level SHA-256 hashes. The deterministic JSON index includes source lines for features, actors, classes, components, states, persistence, interfaces, constraints and conflicts; it is not a complete semantic parser.
- The model must return a bounded manifest with complete source files, a comment-only `requirements.txt`, README and meaningful tests. The app rejects malformed/truncated JSON, missing artifacts, duplicates, traversal, absolute/drive/UNC paths, reserved Windows filenames and linked/reparse output paths.
- Static checks parse Python and reject unsupported imports and suspicious execution operations. Reviewed tests run through explicit worker operations with timeout and bounded diagnostic output. No arbitrary model-suggested shell commands or package installations are executed.
- Independent tests require exact fraction equivalence, invalid-answer handling, one score per question, pause/resume, question sequencing, game-over behavior and restart. Model-written tests additionally address storage and administration. Manual play remains necessary.
- Each run records input hashes, model/request metadata, file hashes, static/test results, repairs and cost snapshot. Failed or partial runs retain useful evidence and are not reported as complete.

The worker is a separate process running as the current user. Static filtering, working-directory restrictions and time/output limits are **not a complete security sandbox**. Review generated code and prefer a disposable Windows environment for untrusted output. Do not disable security software to launch the executable.

## Cost, persistence and evidence

The app conservatively treats USD 1 as the cumulative paid-call ceiling for the assignment. It uses published **peak** rates for `deepseek-v4-pro`, checked on 31 October 2026, even during off-peak periods. Recheck official prices before the live demonstration; see [API verification](docs/api_reference.md).

Before every request, a persistent ledger reserves an intentionally loose UTF-8 input bound, the maximum output cost, a 20% margin and USD 0.001 overhead. This is not an exact token count or a provider-enforced spending cap. Usage is settled using cache-hit input, cache-miss input and output tokens. Reasoning-token detail is not charged twice. Cost displayed by the app is an estimate, not a provider invoice.

The GUI ledger is stored at `%LOCALAPPDATA%\Task1CodeAgent\usage.sqlite3` and survives restarts. Missing usage, a timeout or uncertain billing retains the reservation and blocks further paid calls. Reconcile against authoritative provider usage before continuing; do not delete the ledger to bypass the cap. Calls made outside this app are not automatically discovered and must be included when accounting for the full assignment.

Default GUI output is the user's `Documents\Task1Runs` folder. A run includes:

| Artifact | Purpose |
| --- | --- |
| `normalized_requirements.json` | Full input text, hashes, evidence index and assumptions |
| `manifest.json`, `manifest_<round>.json` | Accepted complete file manifests and repair history |
| `project/` | Materialized source project |
| `static_result.json`, `test_result.json` | Actual validation results when those stages ran |
| `run_summary.json` | Status, provenance, request usage, file hashes and limitations |

Raw run folders are private local evidence by default. Review and sanitize any evidence before sharing; local self-test results can include absolute paths. The original handoff, task archive, application correspondence and personal screenshots are excluded from the public source repository. The two software input documents are preserved in `inputs/`.

## Repository map

| Location | Responsibility |
| --- | --- |
| `launcher.py` | Source/frozen entry point and bundled worker dispatch |
| `src/code_agent/ui.py` | Desktop controls and background-work event queue |
| `input_loader.py`, `requirements.py` | Original input handling and evidence index |
| `model_client.py`, `budget.py` | Official requests, secret-safe errors and persistent accounting |
| `agent.py`, `prompts.py` | Generation, review and bounded repair protocol |
| `workspace_tools.py` | Strict manifest and safe materialization |
| `validator.py`, `worker.py`, `contracts.py` | Static checks, bounded execution and independent game checks |
| `offline.py`, `self_test.py` | Clearly labelled mocked pipeline diagnostic |
| `tests/`, `docs/`, `inputs/` | Verification, report/submission materials and original software inputs |

## Scope and submission

The generated desktop target requests an original animated introduction, menu/help, ten fraction questions, explanation/score feedback, pause/resume/restart, local score/question persistence and separated player/admin responsibilities. The reviewed example implements these behaviors; automated coverage and remaining manual checks are separated in its provenance. First-run admin credentials use local salted hashing when implemented; local roles are not OAuth2.

Cloud microservices, PostgreSQL/Redis/RabbitMQ/Elasticsearch infrastructure, Kubernetes replication, Vault/Istio, production monitoring, migration tooling, 99.99% availability and 1,000-user concurrency are unimplemented source requirements, not verified capabilities. Source inconsistencies and adaptation decisions remain documented.

See the [technical report](docs/technical_report.md), [reference review](docs/reference_review.md), [assistance disclosure](docs/assistance.md), [Bengali understanding guide](docs/understanding_guide.md), [demo script](docs/demo_script.md) and [submission checklist with unsent email](docs/submission.md). The public reference repositories have differing licenses; their actual inspected content and any reuse are documented in the reference review. The task inputs remain attributed to the supplied evaluation materials.
