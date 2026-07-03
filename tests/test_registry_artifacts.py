"""The staged MCP-registry artifacts cannot drift (spec 0123 decision 4).

`launch/registries/server.json` is a committed submission the maintainer
publishes later; between staging and publishing, the repo keeps changing.
These pins keep the artifact true the whole time: valid JSON of the shape
the official registry expects, internally consistent versions, the README
ownership marker the registry's PyPI validation looks for, and — once the
project version leaves the `0.0.0` placeholder — version sync with
`pyproject.toml`.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_JSON = REPO_ROOT / "launch" / "registries" / "server.json"

SERVER_NAME = "io.github.robert-vetter/tessera"


def _server() -> dict[str, object]:
    data = json.loads(SERVER_JSON.read_text("utf-8"))
    assert isinstance(data, dict)
    return data


def test_server_json_has_the_registry_shape() -> None:
    data = _server()
    assert data["name"] == SERVER_NAME
    assert "2025-12-11" in str(data["$schema"])
    packages = data["packages"]
    assert isinstance(packages, list) and len(packages) == 1
    (package,) = packages
    assert package["registryType"] == "pypi"
    assert package["transport"] == {"type": "stdio"}
    repository = data["repository"]
    assert isinstance(repository, dict)
    assert repository["url"] == "https://github.com/robert-vetter/tessera"


def test_server_json_versions_are_internally_consistent() -> None:
    data = _server()
    packages = data["packages"]
    assert isinstance(packages, list)
    (package,) = packages
    assert isinstance(package, dict)
    assert data["version"] == package["version"], (
        "server.json's top-level version and its package version must match"
    )


def test_readme_carries_the_ownership_marker() -> None:
    """The official registry validates PyPI ownership by finding
    `mcp-name: <server name>` in the package README, followed by a boundary
    (whitespace / newline / `-->`)."""
    readme = (REPO_ROOT / "README.md").read_text("utf-8")
    assert re.search(rf"mcp-name: {re.escape(SERVER_NAME)}(\s|-->)", readme), (
        "README.md lost the mcp-name ownership marker (spec 0123 decision 3)"
    )


def test_versions_sync_once_the_project_version_is_real() -> None:
    """`0.0.0` is the unpublished placeholder; the moment the maintainer bumps
    pyproject for the PyPI publish (RUNBOOK step 1), server.json must move in
    the same commit — this is the guard that makes forgetting impossible."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text("utf-8"))
    project_version = pyproject["project"]["version"]
    if project_version == "0.0.0":
        return  # not yet published; server.json stages the suggested 0.1.0
    assert _server()["version"] == project_version, (
        "pyproject version was bumped: update launch/registries/server.json "
        "(both version fields) in the same change"
    )
