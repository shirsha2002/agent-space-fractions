# Delivery status - 31 October 2026

Source repository: https://github.com/shirsha2002/agent-space-fractions (public).

Completed:

- Official deepseek-v4-pro generated Space Fractions from both original inputs.
- Three paid calls: initial generation and two bounded model repairs.
- Unchanged model-only baseline, its failing test, and disclosed operator fixes are
  preserved separately in examples/space_fractions/provenance/.
- Final reviewed game: 47 passing checks. Agent suite: 56 passing tests.
- Local standalone agent and game Windows executables are built.
- Both agent bundles pass packaged offline/Tk checks. A relocated runtime passed
  in Chinese/spaces paths with Python removed from PATH.
- The standalone game started with System32-only PATH and created its SQLite DB in
  a disposable profile; a normal game window was then opened for the owner.
- Conservative cumulative API estimate: USD 0.21462452, using provider-reported
  usage and peak rates. It is not a provider invoice.

- Revision 3 (operator, visual only, no model calls): animated space background,
  restyled screens, inline answer feedback. Recorded in
  examples/space_fractions/provenance/manual_patch_3.json; 47 checks still pass.
  docs/evidence/game_startup.json refers to the previous (revision 2) executable.

Latest local artifacts:

| Artifact | SHA-256 |
| --- | --- |
| dist/current/Task1CodeAgent.exe | 492b95e8cfedf83b77071e74e040577592b9cd4dab42840664da4a9685b9bb32 |
| dist/game/SpaceFractions.exe | 3996bd7da442445a2c263d5ee1ecb5d461ea349a995f8a447c745f0a06fc584e |

The final local ZIP is release/Task1_Submission.zip. It includes both executables,
agent/game source, original software inputs, tests, report, provenance and a
recording/submission guide. The older Task1CodeAgent-preview.zip is the earlier
offline milestone, not the final delivery kit.

Remaining before submission:

1. Complete manual visual/playthrough and clean-Windows/no-Python checks. Internal
   Tk callback tests and System32-only PATH are not a substitute for a clean VM.
2. Record an authentic YouTube demonstration using the real run evidence and
   reviewed game; label saved evidence/time cuts. Do not spend more merely for video.
3. Share the public repository link, attach the executable ZIP
   through an authorized route, and send the reviewed submission yourself.
4. Clarify the provisional local-desktop adaptation if the professor requires the
   supplied cloud services; they remain unimplemented source requirements.

The previous attempted GitHub draft-release/executable upload was rejected by
automatic approval review, which stated only "blocked by policy". That operation
did not run. Source pushes work; the executables are provided locally. No attempt
has been made to bypass that rejection.

See technical_report.md, requirements_traceability.md, submission.md and
demo_script.md for the exact evidence and remaining checks.
