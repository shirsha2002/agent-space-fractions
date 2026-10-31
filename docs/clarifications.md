# Clarifications and provisional decisions

No professor answers to the questions below have been received through this implementation session. These decisions keep development moving; they are not approvals or waivers.

| Question | Current assumption | Consequence / status |
| --- | --- | --- |
| May the supplied cloud/microservices design become modular local desktop software? | Implement separate game, questions, users and admin responsibilities in a local desktop project. | Needs clarification. PostgreSQL/Redis/services and cloud availability remain unimplemented source requirements. A desktop UI alone does not prove services are unnecessary. |
| Does USD 1 cover one demonstration or all development calls? | Apply a cumulative USD 1 cap to every paid assignment call. | Needs clarification. Reserve before each request and preserve uncertain charges across restarts. |
| Must the generated game also be a standalone executable? | Plan packaging for both agent and generated game. | Agent executable is explicit; generated game desktop UI is explicit; a separate game executable is a conservative delivery choice. |
| Is a separate report required for this task? | Include a concise English technical report. | Earlier correspondence mentions a report; Task1-EN.docx specifies no format or page count. |
| What introductory movie is expected? | Request a short original animated desktop introduction with Skip. | No movie asset was supplied; this interpretation needs clarification. |
| What are the question bank, scoring and credentials? | Request approximately ten original fraction questions, one point per correct answer, exact rational comparison, no duplicate scoring, local score persistence and first-run admin credential setup. | Product defaults, not supplied requirements. Local password roles are not OAuth2. |
| Which availability/error-budget target applies? | Make no production SLO claim. | Source gives 99.99% uptime and 1% error budget, which are inconsistent for the same interval. |
| Where is the question schema? | Require question persistence alongside scores. | Traceability names `sql/question_ddl.sql`, while supplied SQL creates `games`; document the mismatch. |
| What is the exact submission time? | Work toward 6 November 2026 as an approximate one-week target from the handoff date. | No confirmed deadline hour or timezone. |

The `Question` class lacks an answer-checking method despite sequence interactions invoking answer checking. The generation contract completes that behavior explicitly. `AdminComponent` appears in the views but not the main component summary; it remains part of the requested desktop behavior.

If the exact model is unavailable or account access is missing, stop the live path and report it. Do not substitute another model or present fixtures as DeepSeek-generated output.
