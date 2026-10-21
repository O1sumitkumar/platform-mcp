## What and why

<!-- What changed, and the reason. Link the issue: Fixes #123 -->

## How it was tested

- [ ] `pytest` passes locally
- [ ] Added or updated a test (bug fixes: one that fails before the fix)
- [ ] Ran `evals/measure.py` (response-shape change); before/after numbers below
- [ ] Ran `evals/tool_use_evals.py` (docstring / instructions / tool-set change)

## User-visible changes

<!-- Tool names, arguments, response fields, config, or docs. Write "none" if none. -->

## Checklist

- [ ] No GCP method that changes state is called
- [ ] New tools go through `register_tool`, with `EXPECTED_TOOLS`, the CI tool count and the README updated
- [ ] No credentials, real project IDs or live log data in code, tests or this description
- [ ] `version` not bumped
