# Source provenance and comparison

Reviewed 31 October 2026 (Asia/Shanghai). The original `Task1.rar` was available locally. Its inventory contained exactly `Task1-EN.docx`, `Architecture_Documentation.md`, and `Architecture_View.md`; these were extracted to `sources/` without modifying the archive. The files in `inputs/` are byte-for-byte copies of the two extracted Markdown inputs.

| Original file | SHA-256 | Comparison with implementation brief |
| --- | --- | --- |
| Architecture_Documentation.md | `111282df7817bca771e53c82ebb053707a3217cb8f11733a2c25b631ca81db55` | Appendix B matches after CRLF/LF and outer whitespace normalization. |
| Architecture_View.md | `77dac057e13f122ddc6fc19294490c6a961f00429b72f15df81a81adc91bdbc8` | Appendix C matches after CRLF/LF and outer whitespace normalization. |
| Task1-EN.docx | `3c430293d13aa558ea9a066f20d43196aafdcf5ed492b8623b3917bd57216c48` | Extracted paragraph text matches Appendix A after interpreting Word nonbreaking-hyphen nodes as hyphens. |

The Word document uses `w:noBreakHyphen` elements. Extracting only `w:t` text would incorrectly turn `deepseek-v4-pro` into `deepseekv4pro` and remove hyphens from repository URLs. The comparison preserved those elements. `sources/Task1-EN.txt` is a normalized reading copy, not a replacement for the Word original.

The exact original second repository is `https://github.com/Windy3f3f3f3f/how-claude-code-works`. Section 4 of the handoff brief has the shorter owner `Windy3f3f3f`; Appendix A and the original Word document agree on `Windy3f3f3f3f`. Reference review follows the original link.

The supplied views contain 11 numbered diagram categories and 13 actual `@startuml` blocks because sequence and collaboration each have two blocks. No standalone Requirements document, complete question bank, scoring specification, movie asset, credentials, or runnable tests were included.

The email screenshot establishes a desktop generated game, an approximately one-week submission period, a video demonstration, and a DeepSeek token cost within USD 1. The handoff records 30 October 2026 as its context date; 6 November is a planning target only. The screenshot does not establish an exact deadline hour. Application correspondence and personal attachments are unnecessary for the software repository and should stay private.
