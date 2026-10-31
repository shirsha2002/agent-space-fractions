# Reference implementation review

Inspected on **31 October 2026** using GitHub repository metadata, pinned raw files, and official API documentation. These are reference observations; no code from the repositories was copied into the implementation. Documentation examples are not proof of behavior in a running commercial product.

## Source identity

The original `Task1-EN.docx` and Appendix A specify `Windy3f3f3f3f/how-claude-code-works`. The shorter `Windy3f3f3f` username in the brief's main reference list returns 404. This review uses the original document's working URL.

| Repository | Inspected commit | Commit date (UTC) | License observed |
| --- | --- | --- | --- |
| [ultraworkers/claw-code](https://github.com/ultraworkers/claw-code) | `f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712` | 2026-10-28 | MIT |
| [Windy3f3f3f3f/how-claude-code-works](https://github.com/Windy3f3f3f3f/how-claude-code-works) | `f4d6505ed9162a0ee6be089190f74c419ecacb19` | 2026-08-17 | MIT |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | `d4dfed4e1c578cfea8bd6e64873e4f5e5b7e36f0` | 2026-10-30 | All rights reserved; linked commercial terms |

## Claw Code: implementation source

The repository currently describes an agent-managed exhibit, but contains a Rust runtime and provider adapters. Inspected files include `README.md`, `LICENSE`, and the following pinned source files:

- [`conversation.rs`](https://github.com/ultraworkers/claw-code/blob/f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712/rust/crates/runtime/src/conversation.rs): `ConversationRuntime`, a `ToolExecutor` interface, cancellation signals, `run_turn`, and a maximum-iteration setting separate model turns from tool execution.
- [`file_ops.rs`](https://github.com/ultraworkers/claw-code/blob/f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712/rust/crates/runtime/src/file_ops.rs): workspace-aware file operations canonicalize paths and check symlink escapes. A plain relative-path check is insufficient.
- [`openai_compat.rs`](https://github.com/ultraworkers/claw-code/blob/f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712/rust/crates/api/src/providers/openai_compat.rs): provider translation, response normalization, timeouts, and request-size checks belong in a client module.
- [`session.rs`](https://github.com/ultraworkers/claw-code/blob/f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712/rust/crates/runtime/src/session.rs) and [`compact.rs`](https://github.com/ultraworkers/claw-code/blob/f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712/rust/crates/runtime/src/compact.rs): persist usage/events and compact context without separating paired tool calls/results.

Applied ideas: separate client, orchestration, workspace tools, and persistent cost state; stop after bounded repair. The project does not reproduce this repository's whole runtime or claim equivalent security.

## How Claude Code Works: educational analysis

Inspected `README_EN.md`, `LICENSE`, and the English chapters on [the loop](https://github.com/Windy3f3f3f3f/how-claude-code-works/blob/f4d6505ed9162a0ee6be089190f74c419ecacb19/en/docs/02-agent-loop.md), [context](https://github.com/Windy3f3f3f3f/how-claude-code-works/blob/f4d6505ed9162a0ee6be089190f74c419ecacb19/en/docs/03-context-engineering.md), [tools](https://github.com/Windy3f3f3f3f/how-claude-code-works/blob/f4d6505ed9162a0ee6be089190f74c419ecacb19/en/docs/04-tool-system.md), and [minimal components](https://github.com/Windy3f3f3f3f/how-claude-code-works/blob/f4d6505ed9162a0ee6be089190f74c419ecacb19/en/docs/13-minimal-components.md).

The analysis separates conversation state from individual query cycles. It describes schema-checked tools, bounded tool-result text, execution feedback in subsequent model context, cancellation, and cost limits. Its minimal-components discussion helps identify what a small agent needs; its commercial-internal claims remain the author's analysis rather than verified source from Anthropic. Applied ideas: explicit output contracts, validation feedback, and small repair context. This implementation uses JSON manifests and a fixed local verification pipeline rather than a general shell-enabled tool ecosystem.

## Anthropic Claude Code: official distribution repository

Inspected [`README.md`](https://github.com/anthropics/claude-code/blob/d4dfed4e1c578cfea8bd6e64873e4f5e5b7e36f0/README.md), [`LICENSE.md`](https://github.com/anthropics/claude-code/blob/d4dfed4e1c578cfea8bd6e64873e4f5e5b7e36f0/LICENSE.md), [`examples/settings/README.md`](https://github.com/anthropics/claude-code/blob/d4dfed4e1c578cfea8bd6e64873e4f5e5b7e36f0/examples/settings/README.md), [`settings-strict.json`](https://github.com/anthropics/claude-code/blob/d4dfed4e1c578cfea8bd6e64873e4f5e5b7e36f0/examples/settings/settings-strict.json), and [`mods/README.md`](https://github.com/anthropics/claude-code/blob/d4dfed4e1c578cfea8bd6e64873e4f5e5b7e36f0/mods/README.md).

This checkout includes distribution guidance, settings examples, and selected plugin/mod source. It is not a complete open-source copy of the product's model client and central agent loop. The strict settings example separates command permissions from sandbox/network configuration. The mod documentation describes hooks with typed contracts and mocked tests. Applied ideas: independently test orchestration against mocked boundaries and state execution limitations clearly. No proprietary implementation or mod source was reused.

## Deliberate simplifications

The application uses a finite generate → materialize → verify → repair loop. It exposes no model-selected shell commands, arbitrary package installation, MCP servers, browser tools, or multi-agent runtime. The documents remain available with normalized requirements so preprocessing does not discard source constraints. Path restrictions and process timeouts reduce mistakes; they do not constitute an operating-system sandbox. Live generation evidence and clean-machine validation must be recorded separately from offline tests.

Current API facts and exact rates are documented in [api_reference.md](api_reference.md).
