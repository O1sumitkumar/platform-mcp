# Contributing to platform-mcp

Thanks for helping. This is a small, deliberately constrained project: a
**read-only** MCP server that lets an agent debug and cost-check GCP. Most of
the rules below exist to protect that guarantee and to keep what the agent sees
small and accurate.

## Where to start

- Issues labelled [`good first issue`](https://github.com/deBilla/platform-mcp/labels/good%20first%20issue)
  are scoped, mechanical, and have an existing pattern in the code to copy.
- [`help wanted`](https://github.com/deBilla/platform-mcp/labels/help%20wanted)
  issues are larger. Comment on the issue with your approach before writing code.
- [`needs-verification`](https://github.com/deBilla/platform-mcp/labels/needs-verification)
  issues were found by reading the code. The first useful contribution is
  confirming or refuting them against a real project. Post what you saw, with
  identifiers redacted.
- Comment on an issue to claim it, so two people don't fix the same thing.

For anything that adds a tool, changes a tool's arguments or response shape, or
adds a dependency, **open an issue first**. These changes affect every user's
context window and are hard to undo after release.

## Setup

Requires Python 3.11+.

```bash
git clone https://github.com/deBilla/platform-mcp.git
cd platform-mcp
python -m venv .venv
./.venv/bin/pip install -e ".[dev]"
./.venv/bin/python -m pytest
```

The test suite needs **no GCP credentials and no network**. It runs the server
through an in-memory MCP client with stubbed GCP objects. If a test you write
needs credentials, it belongs in `evals/`, not `tests/`.

Live checks against a real project are optional (see [Evals](#evals)). Use a
staging or sandbox project, never production.

## The non-negotiables

### 1. Read-only, always

- **Never call a GCP method that changes state.** That includes anything named
  `create_*`, `update_*`, `delete_*`, `patch_*`, `set_*`, `insert_*`, `start_*`,
  `stop_*`, `resize_*`, and the Recommender `mark_recommendation_*` calls (they
  change recommendation state).
- Register every tool through `registration.register_tool`. Never use
  `mcp.tool()` directly. That's what attaches the read-only annotations and the
  audit wrapper.
- Any IAM role you add to `scripts/setup-service-account.sh` or the README must
  be a viewer/reader role. If a feature needs more than read access, it doesn't
  belong in this project.

The identity is the real guarantee (see "Security model" in the README); the
code is the second layer. A PR that weakens either one won't be merged.

### 2. stdout is the protocol

In stdio mode stdout carries JSON-RPC. A stray `print()` corrupts the stream
and drops the client connection. Log through `observability.logger` (stderr).
The only `print` calls allowed are in CLI paths that run before the server
starts (`setup`, `doctor`).

### 3. No credentials, real data, or recorded responses in the repo

- No service-account keys, tokens, project IDs, or resource names from a real
  organisation in code, tests, fixtures, or issue text. Use `demo-staging` /
  `demo-prod` as in `tests/conftest.py`.
- Output from `evals/measure.py` contains live log lines. It's git-ignored for
  a reason, so redact before quoting any of it.
- CI scans for credential-shaped strings and fails the build if it finds one.

## Writing or changing a tool

Every tool follows the same contract. Read one existing module end to end
(`tools/inventory_tools.py` is the shortest) before writing a new one.

**Arguments**
- Take an optional `environment: str = ""` and resolve it with
  `config.resolve_environment()`. Never guess a project.
- Bound every `limit` with `max(1, min(limit, MAX))`.
- Reject invalid enum-like arguments with a `ValueError` naming the valid
  values. Don't fall back silently to a default: a wrong answer that looks
  plausible is worse than an error.

**Response**
- Return a `dict` that includes `environment` and `project`, plus `count` for
  lists. The audit log reads these fields.
- Keep responses small. Drop empty and duplicated fields, and put bulky fields
  (e.g. labels) behind an opt-in argument.
- **When you truncate, cap, round or skip, say so in the response.** Existing
  examples: `stopped_for_size`, `message_truncated`, `points_per_series_cap`,
  `period_applied`, `skipped_calls`. The agent can't see what was left out
  unless the response tells it.

**Errors**
- Signal failure by raising, never with a success-shaped dict carrying a
  `status` field. Raise `PlatformMCPError` with a message an agent can pass on
  to a human: which environment, which identity, and the exact command or role
  that fixes it. `errors.py` shows the style.

**Docstrings**
- The docstring becomes the tool description the model reads, so it's the
  highest-leverage text in the project. Describe what the tool returns, when to
  use it, and every argument with an example value. If your change alters
  behaviour that a docstring or the server instructions describe, update them
  in the same PR.

**Clients**
- Add GCP clients to `clients.py` as a cached getter that takes an
  `Environment`, and import the SDK inside the function so startup stays fast.
- Pass a timeout on every network call.

**Registering**
- Call `register_tool` in the module's `register()`. If you add or remove a
  tool, update `EXPECTED_TOOLS` in `tests/test_protocol.py`, the tool count in
  `.github/workflows/ci.yml`, and the tool list in the README.

## Tests

Every behaviour change needs a test. Bug fixes need a test that fails before the
fix.

| What you changed | Where the test goes |
| --- | --- |
| Config parsing, environment resolution | `tests/test_config.py` |
| Error translation | `tests/test_errors.py` |
| Response shape, truncation, field selection | `tests/test_payload_shape.py` (stub objects, not recorded data) |
| Tool registration, schema, annotations | `tests/test_protocol.py` |
| Audit log | `tests/test_observability.py` |
| Helpers in `formatting.py` | `tests/test_formatting.py` |

Fixtures in `tests/conftest.py` clear the `lru_cache`d settings around every
test and point the config at an absent file, so your local
`~/.config/platform-mcp/config.toml` never leaks into a run. Use the
`configured` fixture rather than setting environment variables yourself.

## Evals

`evals/` holds the checks that need live GCP. You don't have to run them, but
say in your PR whether you did:

- `evals/measure.py <environment>` records payload size and latency for every
  tool. Run it if you changed a response shape, and put the before/after
  numbers in the PR.
- `evals/tool_use_evals.py` drives the Claude Code CLI against the server and
  checks which tool the agent called, and against which environment. Run it if
  you changed a docstring, the server instructions, or which tools are
  registered. Wording changes there move agent behaviour more than code changes
  do.

See `evals/README.md` for details.

## Code style

- Match the surrounding code. Type hints on public functions,
  `from __future__ import annotations`, standard library before third party.
- Comments explain **why**, especially when the reason came from a measurement
  or an incident. Look at the comments on `_format_resource` and `_MAX_PAYLOAD_CHARS`
  for the expected level of detail. Don't add comments that restate the code.
- No new runtime dependency without an issue first. Provider SDKs (for future
  AWS/Azure work, see #16) go in optional extras, not `dependencies`.

## Commits and pull requests

1. Branch from `main`. One logical change per PR.
2. Write commit subjects in the imperative, describing the behaviour, not the
   file ("Raise on unknown duration units", not "Update formatting.py"). Use
   the body for the why.
3. Reference the issue (`Fixes #5`).
4. In the PR description, include:
   - what changed and why
   - how you tested it (`pytest` output, plus any eval/measure run)
   - any change to tool names, arguments, or response fields (these are
     user-visible API)
5. CI must pass: tests on Python 3.11–3.13, the secret scan, and the package
   build/smoke test.
6. Update `README.md` when behaviour, configuration, or setup changes.

The maintainer handles versioning and releases. Don't bump `version` in
`pyproject.toml` or `server.json` in a feature PR.

## Reporting bugs and security issues

- **Bugs:** open an issue with the tool name, arguments, what you expected, and
  what came back, with project IDs and log content redacted. The audit log
  (`~/.local/state/platform-mcp/audit.jsonl`) records the tool, environment,
  duration and error type of each call, which usually pins it down.
- **Anything that could let the server write to GCP, leak credentials, or
  expose data across environments:** don't open a public issue. Report it
  privately through GitHub's
  [security advisory](https://github.com/deBilla/platform-mcp/security/advisories/new)
  form.

## License

By contributing you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
