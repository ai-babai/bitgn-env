# Temporal Anchor Policy

Purpose: eliminate date drift in answer-only and write flows.

## Deterministic anchor rules

1. If instruction provides explicit anchor date/time, use it.
2. Otherwise, use latest `context.time`.
3. Do not use ambient/system date for relative-date arithmetic.

## Relative expressions covered

- `today`, `tomorrow`, `day after tomorrow`, `yesterday`
- `in N days/weeks/months/years`
- `N days ago` and equivalent forms

## Pre-finalization self-check

Before `report_completion`, construct and validate:

- `anchor=<YYYY-MM-DD>`
- `expression=<original relative phrase>`
- `result=<YYYY-MM-DD>` (or requested format)

Submission date must equal computed `result`.

## Output format adaptation

- Compute in ISO internally.
- Convert to requested output format only at the last step (for example, `DD-MM-YYYY`).

## Regression checklist

- `t41`-like tasks always match anchor-based result.
- Presence of `context.time` suppresses system-date fallback.
