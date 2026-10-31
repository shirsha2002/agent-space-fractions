# Start here - Task 1 delivery

The local `release/Task1_Submission.zip` contains both Windows executables at its
root, plus all agent/game source, original software inputs, tests, report and
authentic generation evidence. Extract the whole ZIP to a normal writable folder.

## Play the game

1. Double-click **SpaceFractions.exe** in the extracted delivery kit.
2. Choose **Register New Player**, enter a local username and a password of at
   least eight characters, then log in.
3. Watch or skip the short intro and select **Play Game**. Number keys select
   answers, Enter advances after an answer, and Escape pauses/resumes.
4. Help, score history and Play Again are available. Administrator setup is
   separate: choose your own admin password using the first-time setup button,
   then log in as `admin` to edit questions. No working default password is shipped.

No API key, internet connection or pre-installed Python is needed merely to play
the packaged game. Local accounts/questions/scores live in the Windows user's
application-data folder.

## Inspect the agent

Double-click **Task1CodeAgent.exe**. It opens in a labelled offline diagnostic mode.
That diagnostic exercises the generation/repair plumbing without paid calls; it
is separate from the real Space Fractions output already supplied in this kit.

The actual official DeepSeek run is recorded under
`examples/space_fractions/provenance/`. It used one generation and two model repairs.
The model-only final baseline had one wrong test vector; disclosed operator fixes
and extra regression tests produced the reviewed final version. Do not describe
the model-only baseline as an autonomous passing result.

The conservative three-call API estimate is **USD 0.21462452** from provider-reported
usage at peak rates. It is not a provider invoice. No further API call is needed
for playing, inspecting the evidence, or recording a demonstration.

## Verification and source

- 56 agent tests pass.
- 47 reviewed-game checks pass, also through the packaged agent runner with
  System32-only PATH.
- The packaged client passed a read-only official model-access check.
- Both agent bundle types and standalone game startup were checked on the
  developer's Windows machine. That machine still has Python installed.
- Manual visual/playthrough and clean-Windows/no-Python checks remain pending.

The portable agent check needs only Windows PowerShell and the supplied EXE:

```powershell
.\scripts\verify_windows.ps1 -PackageRoot .
```

Only add `-ConfirmCleanWindows` on a machine you know has no pre-installed Python.
It records your assertion separately from the automatic results. See
`docs/packaging.md` for the complete procedure.

Source and build instructions are in `README.md`. The reviewed game source is
`examples/space_fractions/project/`. Its three immutable model manifests and the
operator patch records are adjacent under `provenance/`. No API key, payment
receipt or private account balance is included.

## Finish submission

1. Complete visible gameplay/admin checks and the clean-Windows check.
2. Record the authentic demonstration using `docs/demo_script.md`; label saved
   run evidence and time cuts. Upload it to your YouTube account and verify the link.
3. Share the full ZIP and/or share the public repository:
   https://github.com/shirsha2002/agent-space-fractions
4. Complete the unsent email in `docs/submission.md`, replace every placeholder
   and send it yourself. The report is `docs/technical_report.md`; Bengali
   explanation is `docs/understanding_guide.md`.

The earlier automated GitHub executable-release upload was rejected by automatic
approval review with only "blocked by policy" stated. Source pushes succeeded;
the binaries are supplied locally. No email or YouTube video has been sent.
