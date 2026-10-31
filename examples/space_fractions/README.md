# Space Fractions: real generation and reviewed delivery

- Final source: `project/` (standard-library desktop game).
- Model: official `deepseek-v4-pro`.
- Input: the two original architecture documents, whose hashes are recorded.
- Calls: one generation + two model repair rounds; no later model calls.
- Reviewed result: 47 passing checks (4 host contract checks, 36 model-authored
  checks with disclosed corrections, and 7 operator-authored regressions).
- Conservative application cost estimate: USD 0.21462452 at peak rates.
- Standalone Windows build: local `dist/game/SpaceFractions.exe`; large binaries
  are provided locally rather than committed to source history.

## Provenance

`provenance/manifest_0.json`, `manifest_1.json` and `manifest_2.json` are the
unchanged actual model outputs. The first response triggered static rejection
of direct cleanup operations in generated tests. Model repair 1 still contained
a contradictory fraction-equivalence test. Model repair 2 corrected that issue,
but left an invalid test vector expecting a valid update to fail and several
local role/UI edge cases.

`model_only_baseline_test_result.json` is an actual repeat check of unchanged
manifest 2 in a temporary workspace: 40 tests, one failure. It is not hidden or
relabeled as a fully autonomous success. The original model manifests remain
reference data and are not the reviewed build source.

`manual_patch_1.json` and `manual_patch_2.json` record Codex's disclosed operator
changes with before/after hashes, reasons and timestamps. They cover authenticated
question/password updates, editing text distractors, a genuinely invalid
transaction-preservation test vector, pause/binding cleanup, intro timing/art,
recent-score ordering and additional UI/storage regression tests. They caused no
additional model calls. `manifest_manual_*.json` and final `manifest.json` identify
those reviewed states. `run_summary.json` records both the DeepSeek requests and
manual adjustments; `test_result.json` is the real final passing result.

`usage_ledger.json` contains provider-reported token usage and conservative
application-estimated peak-rate charges. No API key, payment receipt, account
balance, local user directory, or provider invoice is included. The normalized
requirements retain original document text and evidence-linked assumptions.

## Launch

On the Windows delivery kit, double-click `SpaceFractions.exe`. No API key is
needed to play. Choose Register New Player, use a local username and a password
of at least eight characters, then log in. Admin setup is separate and initially
unconfigured; choose your own administrator password before using that role.

From source with Python 3.13/Tkinter: `python main.py` inside `project/`.
Model and operator tests: `python -m unittest discover -s tests` from that same
folder. The host's four independent rules are supplied by the agent runner.

This is a provisional single-user local-desktop adaptation. Cloud services,
OAuth2, production availability, 1000-user concurrency and cross-platform builds
are not claimed. Manual visual/playthrough and clean-Windows checks remain pending.
