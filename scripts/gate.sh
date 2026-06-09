#!/usr/bin/env bash
# The canonical quality gate — the single source of truth that BOTH the local
# /verify command and CI (.github/workflows/ci.yml) run, so a green local gate
# always means a green CI gate. Format, lint, type-check, tests, in that order.
#
# (The eval harness and the gitleaks secret scan are run separately by each
# caller, matching CI's job layout.)
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
