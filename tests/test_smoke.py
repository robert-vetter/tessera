"""Smoke test: the package imports and exposes a version.

Trivial by design — its job is to prove the toolchain runs green on a
near-empty project, per spec 0001. Real tests arrive with real features.
"""

import tessera


def test_version_present() -> None:
    assert isinstance(tessera.__version__, str)
    assert tessera.__version__
