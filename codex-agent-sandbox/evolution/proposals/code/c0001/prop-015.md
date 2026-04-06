# Code proposal prop-015

- code_version: c0001
- prompt_version: p0018
- run_id: run_20260331T080805Z_795d9c2d
- benchmark: bitgn/sandbox
- ts: 2026-03-31T08:22:51.409712+00:00

## Failed tasks
| Task | Fail group | Note |
|---|---|---|
| t03 | other | FileAdded body: expected "# Invoice #13\n\nAmount: $190\n\nThank you for your business!" got "# Invoice #13\n\nAmount: $190\n\nThank you for your business!\n" |
| t05 | other | answer contains expected answer but is not precise. Expected: 'work/tmp/client-note.md' |

## Proposals (requires user approval)
- `t03`: `runner_safety_improvement`
  - fail: FileAdded body: expected "# Invoice #13\n\nAmount: $190\n\nThank you for your business!" got "# Invoice #13\n\nAmount: $190\n\nThank you for your business!\n"
  - code fix: Tighten runtime checks and completion gating for this failure type.
- `t05`: `runner_safety_improvement`
  - fail: answer contains expected answer but is not precise. Expected: 'work/tmp/client-note.md'
  - code fix: Tighten runtime checks and completion gating for this failure type.
