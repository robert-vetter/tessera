#!/usr/bin/env bash
# The canonical quality gate — the single source of truth that BOTH the local
# /verify command and CI (.github/workflows/ci.yml) run, so a green local gate
# always means a green CI gate. Format, lint, type-check, tests, then the eval
# faithfulness floor, in that order.
#
# The eval runs LAST: a code regression surfaces first as a localized pytest
# failure, and the holistic floor breach (an emitted claim unsupported by its
# evidence) second. `tessera-eval` exits non-zero when faithfulness < 1.0 on any
# battery (ADR 0005/0007), so with `set -e` that breach fails the gate here —
# the floor the project claims gates the build now actually does, in CI too,
# not only in the manual /verify step.
#
# (The gitleaks secret scan stays a separate step in each caller — it needs the
# pre-commit environment cache and is not part of the code-quality gate.)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== ruff format --check =="
uv run ruff format --check .

echo "== ruff check (lint) =="
uv run ruff check .

echo "== mypy (strict) =="
uv run mypy src tests

echo "== pytest =="
uv run pytest

# The one hard floor: faithfulness == 1.0 on every battery, or the build fails.
# No --record here; recording history is a deliberate, --note-paired checkpoint.
echo "== tessera-eval (faithfulness floor) =="
uv run tessera-eval
