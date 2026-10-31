# Optional local key handoff for an operator-assisted live run

The main desktop application's API-key field remains session-only. For this
assisted implementation session, `scripts/local_key_setup.py` provides a separate
masked local window. Saving a key there is an explicit local action. It does not
make a paid request and never sends a key through chat.

The helper uses Windows DPAPI with the current-user scope and no interactive
protection prompt. The encrypted handoff is stored at
`%LOCALAPPDATA%\Task1CodeAgent\live_key.dpapi`, outside the repository. It is not
a password manager or a claim of protection against programs running as that
same Windows user. The handoff is removed after the authorized live task.
Native temporary buffers are cleared; Python strings are still ordinary
in-process secret data and must never be serialized or logged.

References: [CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)
and [CryptUnprotectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata).

Developer commands:

```powershell
.\.venv\Scripts\pythonw.exe scripts\local_key_setup.py
.\.venv\Scripts\python.exe scripts\run_live.py preflight
.\.venv\Scripts\python.exe scripts\run_live.py generate
# Alternatively, explicitly start the real desktop UI for the assisted run:
.\.venv\Scripts\pythonw.exe scripts\desktop_live_run.py --authorized-live-run
# Inspect all generated source before this next command:
.\.venv\Scripts\python.exe scripts\run_live.py verify --run-directory 'runs\run_\<id>' --reviewed-source
```

The CLI uses the same official client, persistent cumulative USD 1 ledger,
manifest validation, worker and repair limit as the desktop UI. The operator
generation uses a 24,000-token output ceiling to leave room for complete game
source; this ceiling is recorded in the run summary and every reservation.
The normal GUI default remains 16,000. Model access and account balance are
checked using read-only official endpoints before generation. Search API
examples are not needed for this task.

`account_preflight_private.json` may contain balance information and stays in the
ignored private run directory. Do not publish it or a payment receipt. The receipt
and encrypted handoff patterns are excluded by `.gitignore`. A funded account is
not itself evidence that generation has succeeded; only actual run and test
results establish that outcome.
