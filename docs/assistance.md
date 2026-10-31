# Authorship, tools and source attribution

Shirsha Mitra supplied the task archive, implementation handoff and project direction. Codex assisted with requirements interpretation, reference research, implementation, automated tests, packaging instructions and documentation during this session. Repository history records the code and documentation actually produced; it does not establish unaided authorship.

The runtime agent's use of DeepSeek is a separate part of the evaluated system. A project is described as DeepSeek-generated only when a genuine authorized run has a recorded input hash, exact model, response provenance, file manifest, usage and validation results. Offline fixtures are synthetic test data. No fixture is a successful live generation, and no manually implemented game should be relabelled as runtime output.

The original architecture and UML inputs came from the supplied evaluation materials. Reference findings and any reused source belong in `reference_review.md`; using architectural ideas does not imply copying an implementation. Preserve upstream licenses if code is ever incorporated. Do not claim every reference is open source merely because its repository is public.

Before submission, Shirsha should run the project, review the code, verify every claim and be able to explain the generation loop, file validation, budget accounting, game states, scoring and limitations. The technical report should accurately describe any later personal changes or manual edits to generated output.


The authentic run now exists: official deepseek-v4-pro produced the complete game,
with two model repairs. Its model-only final baseline had one incorrect test
vector. Codex then made two disclosed operator patch revisions, with before/after
hashes, covering local authorization, UI lifecycle and regression tests. All three
model manifests remain unchanged. The final reviewed source passes 47 checks;
this is not described as fully autonomous success or unaided student authorship.

After Codex's usage limit was reached, Claude Code (Anthropic) continued the
session for the owner: it re-verified the agent and game suites, made the
visual-only operator revision 3 (animated space background and restyled game
screens, recorded with before/after hashes in `manual_patch_3.json`), rebuilt
the game executable and release kit, and updated these documents. Commits it
produced carry a Co-Authored-By trailer.
