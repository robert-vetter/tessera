"""Ed25519 signing over the bundle root (spec 0135, ADR 0032).

Signing binds a bundle's sealed root to a keyholder, so re-sealing a tampered
bundle is no longer free for anyone but that holder. It needs a real crypto
library (libsodium via PyNaCl) and so lives behind the optional ``sign``
extra, imported lazily here — exactly the ``cloud``/``salt``/``agent``
opt-in pattern. **Verification** never comes through this module: it uses the
pure-Python :mod:`tessera.bundle.ed25519`, so ``tessera verify`` stays
stdlib-only (no secret ever touches the verify path).

What is signed is the UTF-8 bytes of ``integrity.root`` — which already
commits every sealed section (ADR 0031), so signing it signs the bundle. The
signature is an attestation *over* the root and never enters the manifest.
"""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Any

SIGN_ALGORITHM = "ed25519"
DEFAULT_KEY_PATH = Path("var/keys/bundle_signing.key")


class SigningUnavailableError(RuntimeError):
    """Raised when signing is requested without the ``sign`` extra installed —
    a clean, actionable error, never a bare ImportError traceback."""


def _signing_key_class() -> Any:
    """The libsodium ``SigningKey`` class, imported lazily. Returns ``Any``
    because PyNaCl is an optional, untyped dependency present only with the
    ``sign`` extra — the surrounding functions guard every use behind an
    existence check, and the RFC-vector + cross-check tests pin behaviour."""
    try:
        from nacl.signing import SigningKey
    except ModuleNotFoundError as error:  # pragma: no cover - covered via monkeypatch
        raise SigningUnavailableError(
            "signing needs the 'sign' extra — install it with "
            "`uv sync --extra sign` (verification never needs it)"
        ) from error
    return SigningKey


def _root_bytes(bundle: dict[str, object]) -> bytes:
    integrity = bundle.get("integrity")
    if not isinstance(integrity, dict) or "root" not in integrity:
        raise ValueError("cannot sign an unsealed bundle (no integrity.root)")
    root = integrity["root"]
    if not isinstance(root, str):
        raise ValueError("integrity.root is not a string")
    return root.encode("utf-8")


def generate_keypair(path: Path = DEFAULT_KEY_PATH) -> str:
    """Generate an Ed25519 keypair, write the 32-byte seed (hex, ``0600``) to
    ``path`` and the public key (hex) to ``path.pub``, and return the public
    key hex. Refuses to overwrite an existing key (a keyholder never silently
    loses a key)."""
    signing_key_cls = _signing_key_class()
    pub_path = path.with_suffix(path.suffix + ".pub")
    if path.exists() or pub_path.exists():
        raise FileExistsError(
            f"a signing key already exists at {path} — refusing to overwrite"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    key = signing_key_cls.generate()
    seed_hex = bytes(key).hex()
    public_hex = bytes(key.verify_key).hex()
    path.write_text(seed_hex, encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600 — the secret is owner-only
    pub_path.write_text(public_hex, encoding="utf-8")
    return public_hex


def sign_bundle(
    bundle: dict[str, object], key_path: Path = DEFAULT_KEY_PATH
) -> dict[str, object]:
    """Return a copy of ``bundle`` with a filled ``signature`` section: an
    Ed25519 signature over ``integrity.root``. Requires the ``sign`` extra and
    an existing key (:func:`generate_keypair`)."""
    signing_key_cls = _signing_key_class()
    if not key_path.exists():
        raise FileNotFoundError(
            f"no signing key at {key_path} — run `tessera bundle keygen` first"
        )
    seed = bytes.fromhex(key_path.read_text(encoding="utf-8").strip())
    key = signing_key_cls(seed)
    signed = key.sign(_root_bytes(bundle))
    out = dict(bundle)
    out["signature"] = {
        "algorithm": SIGN_ALGORITHM,
        "public_key": bytes(key.verify_key).hex(),
        "signature": signed.signature.hex(),
    }
    return out
