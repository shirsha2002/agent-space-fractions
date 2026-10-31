# Task 1 technical report - Windows Code Agent and Space Fractions

Project owner: Shirsha Mitra. Implementation, review and documentation were assisted by Codex. The runtime game was genuinely generated through the official DeepSeek API; disclosed operator adjustments are distinguished from model output below. Status: 31 October 2026.

## Objective and scope

The task requires a simplified Windows desktop Code Agent using `deepseek-v4-pro`, taking both original architecture Markdown files and producing full project source, a dependency manifest, README and tests. The follow-up email requires a desktop game, YouTube demonstration and token cost within USD 1. The agent and reviewed Space Fractions game now have local Windows executables. Clean-Windows/no-installed-Python verification, manual visual checks and the video remain pending.

The supplied source describes web/cloud microservices. The implementation uses modular local desktop responsibilities as a provisional adaptation; professor approval of that adaptation has not been obtained. SQLite/local roles are not PostgreSQL replication or OAuth2, and no cloud availability or 1000-user concurrency claim is made. Every such source requirement remains mapped in the traceability table.

## Source and reference study

The original archive was compared with the handoff appendices. Both Markdown files are preserved byte-for-byte, including in Git blobs. Word task extraction matches after interpreting its nonbreaking-hyphen nodes. There are 13 UML blocks across 11 numbered categories. The original Windy repository owner corrects a typo in the brief's main list. See `source_comparison.md`.

`reference_review.md` records actual inspected commits, licenses and files. Claw Code exposes useful Rust runtime/client/file/context mechanisms; the Windy repository is educational analysis; the official Anthropic repository does not expose the complete commercial engine. No reference implementation code was copied. The simplified design separates orchestration, provider access, workspace tools, validation and persistent accounting.

## Agent implementation

The application uses Python 3.13's standard library and Tkinter. Both inputs are validated as distinct, readable nonempty UTF-8 Markdown documents within size limits. Their original bytes are hashed; full text accompanies a deterministic JSON evidence index for purpose, actors, features, classes, states, interfaces, persistence, constraints, artifacts and conflicts. The index is not presented as complete semantic understanding.

The provider client fixes the official endpoint and exact model, explicitly requests non-thinking JSON, bounds output and rejects incomplete responses. A manifest contains complete path/content entries. Before writing, the agent rejects malformed JSON, duplicate keys/case-colliding names, missing artifacts, excessive sizes, traversal, absolute/drive/UNC paths, reserved Windows filenames, file/directory collisions and symlink/junction/reparse escapes. Fresh run folders preserve unrelated work.

The desktop UI includes masked session-key input, input/output selectors, start/cancel, logs, progress, costs and result links. Network work and validation run off the Tk event thread. Generation stops for source review before execution. The operator-assisted live run used this same source desktop UI and engine; the separate local key-handoff helper enabled the owner to enter the secret without putting it in chat. It used user-bound Windows encryption outside the repository. The ordinary GUI remains session-only.

The loop is index - generate - validate/materialize - source review - tests - bounded repair. Two model repairs are the configured maximum. Source-review findings are distinct from test results, so passing tests are not relabeled as failed tests merely to request improvements. Reviewed manual patches retain original model manifests, before/after hashes, reasons, reviewer and timestamps, and do not increase paid calls.

## Authentic live run and review outcome

Run ID: `20261031T073223Z_f038d3d8`. Provider/model: official `deepseek-v4-pro`. It used three paid calls: initial generation and two model repairs.

| Stage | Observed result |
| --- | --- |
| Initial response | Full manifest returned; static policy rejected direct `os.remove`/`os.rmdir` cleanup in generated tests. |
| Model repair 1 | Static pass; 32 checks ran, with one contradictory fraction-equivalence test failing. Source review also found ambiguous choices, initial admin/login weaknesses and keyboard/lifecycle issues. |
| Model repair 2 | Revised bank/auth/UI; unchanged model-only baseline ran 40 checks with one invalid transaction-preservation test vector still failing. |
| Disclosed operator review | Corrected that invalid vector; enforced authenticated local question/password updates; supported text distractor editing; fixed pause/input/lifecycle handling; added timed intro/Canvas planet art and recent-score ordering; added storage/UI regressions. |
| Visual operator revision 3 | Owner-requested, visual only (Claude Code assisted): animated parallax starfield/nebula background, restyled screens, inline answer feedback, animated rocket intro. Rules, storage and authorization unchanged; recorded in `manual_patch_3.json`; no model calls. |
| Final reviewed output | 47 checks passed: 4 host independent rules, 36 model-authored checks with disclosed corrections, and 7 operator-authored regressions. |

This is not claimed as perfect autonomous generation. `examples/space_fractions/provenance/` preserves all three actual model manifests and the model-only failing baseline separately from final reviewed source. No prewritten complete game was embedded or copied as an alleged model result. The static-round-0 evidence file explicitly identifies itself as a recomputation from the preserved manifest; the baseline test file is an actual repeat execution of unchanged model round 2, not a fabricated original timestamp.

## Game behavior and evidence

The reviewed game provides player registration/login, one-time administrator setup, skippable animated introduction, main menu, help/history, ten fraction questions, explanations, one point per correct answer, duplicate-submit protection, playing/paused/game-over states, number-key/Enter/Escape controls, restart and ending feedback. SQLite stores questions, credentials and scores under the Windows user's application-data directory. Admin editing validates before writing; unauthorized/logged-out updates and password resets are rejected through local session checks.

Question evaluation uses exact `fractions.Fraction` comparison. Local passwords use salted PBKDF2-HMAC-SHA256 with 100000 iterations and constant-time comparison. This is a local educational prototype; it does not protect the SQLite file from its Windows account owner, implement OAuth2, or claim production identity security.

The agent suite passed 56 tests, including path/junction defenses, malformed output, bounded repair, cancellation/timeouts, secret-safe errors, cumulative/uncertain budget behavior, internal Tk responsiveness/review gates, encrypted local handoff and manual-patch provenance. The game passed 47 checks, including real disposable Tk callbacks for paused input, score-once behavior, admin denial, logout and edit persistence. Internal widget tests are not visual screenshot inspection or a clean-machine playthrough.

## Cost and accounting

Provider-reported usage totals: 40291 prompt tokens (640 cache-hit; 39651 cache-miss), 40974 completion tokens, 0 reasoning-detail tokens, 81265 total tokens. The persistent ledger records all three requests as settled.

The conservative application estimate at verified peak rates is **USD 0.21462452**, below the cumulative USD 1 cap. Peak USD per million tokens: cache hit 0.044, cache miss 1.32, output 3.96. Reasoning detail is not counted twice. This is an application estimate from provider-reported usage, not a reconciled provider invoice. No extra calls were made for manual fixes or to obtain a nicer recording. The owner purchased API credit separately; a recharge amount is not the assignment's token expense, and no receipt or balance data is published.

Before each call the ledger reserves a conservative UTF-8 byte-derived input bound, maximum output, 20% margin and USD 0.001 overhead. Pending/uncertain charges persist across restarts and block automatic retries. The operator generation used a recorded 24000-token ceiling; normal GUI default is 16000. Published pricing and parameters are linked in `api_reference.md`.

## Windows delivery and limits

PyInstaller bundles the agent runtime, supported standard-library runner, Tkinter and original inputs. The runner supports generated tests/game execution without assuming `python` on PATH. Both agent bundle types pass packaged offline/Tcl-Tk checks on the development host. A relocated agent also passed with Chinese/spaces paths and System32-only PATH. The game has a separate standalone Windows build. Packaging scripts verify source provenance and disclose operator changes.

A live old executable can remain locked on Windows, so `build_windows.ps1 -OutputDirectory dist/current` provides a fresh build location without interrupting the active session. Building the game requires the pinned developer toolchain; targets need only the packaged executable. Process time/output limits and static/path checks are not an OS security sandbox. Generated code was reviewed before execution; Windows Sandbox/clean-machine and manual visual evidence are still required.

No cloud services, high availability, load/chaos testing, migration tooling, production SLO or cross-platform build was verified. The source's 99.99% uptime versus 1% error budget, missing question-check signature, Admin summary gap and question/game SQL mismatch remain recorded. The final video and evaluator repository access must be completed before submission. An unsent email and exact checklist are in `submission.md`.


Additional packaged checks: all 47 reviewed-game tests also passed through the current frozen agent runner with PATH restricted to Windows System32. The packaged client accessed the required model through a read-only official GET /models probe. The standalone game window and disposable SQLite initialization were observed from the packaged executable under the same restricted PATH. These add no paid chat calls and still do not establish a clean-machine or manual visual playthrough.
