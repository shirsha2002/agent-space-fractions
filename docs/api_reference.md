# Official DeepSeek API verification

Checked on **31 October 2026** against official documentation. This verifies the published interface, not access through a funded account. No paid model request was made for this review.

## Model and cost snapshot

The required model name is `deepseek-v4-pro`; the listed model version is `DeepSeek-V4-Pro-0813`. The documentation lists a 1M context window, a maximum output of 384K tokens, JSON output, and tool calling. [Models and pricing](https://api-docs.deepseek.com/quick_start/pricing/).

USD per **1,000,000 tokens**:

| Category | Peak | Off-peak |
| --- | ---: | ---: |
| Input, cache hit | 0.044 | 0.022 |
| Input, cache miss | 1.32 | 0.66 |
| Output | 3.96 | 1.98 |

The published peak periods are weekdays 01:00–04:00 and 06:00–10:00 UTC, excluding Chinese public holidays. Other periods are off-peak. This application's conservative estimate uses **peak rates at all times**; it is not a provider invoice. Recheck rates before the live demonstration. [Pricing rules](https://api-docs.deepseek.com/quick_start/pricing/).

## Request and response contract

Use `POST https://api.deepseek.com/chat/completions`, JSON content, and an `Authorization: Bearer ...` header. Keep the key outside project files and logs. [Official first-call example](https://api-docs.deepseek.com/).

The request specifies `model`, `messages`, `max_tokens`, `stream: false`, and `response_format: {"type": "json_object"}`. `max_tokens` accepts 1–393216; defaults differ by thinking mode, so always set it explicitly. Treat any `finish_reason` other than `stop` as incomplete. Response usage contains `prompt_tokens`, `completion_tokens`, `total_tokens`, `prompt_cache_hit_tokens`, and `prompt_cache_miss_tokens`; the input total equals hits plus misses. `completion_tokens_details.reasoning_tokens` is a breakdown of completion usage, not an additional charge to add again. Reject inconsistent usage and retain the request reservation when billing cannot be established. [Chat completions schema](https://api-docs.deepseek.com/api/create-chat-completion/).

The prompt must explicitly request JSON and show the desired structure. JSON mode can return whitespace-only content even with a normal stop; reject that result. Valid JSON still requires local schema, file-path, and completeness checks. [JSON output guide](https://api-docs.deepseek.com/guides/json_mode/).

Thinking is enabled by default. `thinking: {"type": "disabled"}` explicitly selects non-thinking operation; this is used to make the generation output budget easier to control. It does not change the required model. [Thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/).

## Account checks and failures

`GET /models` can verify that the required model is accessible to the account. [Model listing](https://api-docs.deepseek.com/api/list-models/). `GET /user/balance` reports balance availability and currency; it is not a per-request billing ledger. [Balance endpoint](https://api-docs.deepseek.com/api/get-user-balance/).

Relevant failure statuses are 400/422 (request), 401 (authentication), 402 (balance), 429 (rate), and 500/503 (service). This project does not automatically retry a paid request after uncertain billing. [Official error codes](https://api-docs.deepseek.com/quick_start/error_codes/).

## Project accounting choices

The USD 1 ceiling is treated as cumulative for the whole assignment until clarified. Reserve a conservative input-byte bound plus maximum output and margin before every request. Persist reservations across restarts. Account for all output tokens once; use reported cache categories when present. A timeout, unreadable response, or missing usage may still have been billed, so retain the reservation and require reconciliation. These are project safeguards, not claims that DeepSeek provides a hard USD spending cap.


Subsequent live verification: the owner funded an account and configured a key locally. Three actual official deepseek-v4-pro chat calls completed; recorded usage and reviewed output are in ../examples/space_fractions/provenance/. The packaged agent also passed a read-only GET /models probe. This later live work is separate from the no-paid-call reference review above.
