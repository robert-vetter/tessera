"""Tests for bundle signing and pure-Python verification (spec 0135, ADR 0032).

Two layers are pinned. The pure-Python RFC 8032 verifier is checked against
the RFC's own §7.1 test vectors and rejects any flipped bit — that runs with
no extra, everywhere. The signing round-trip (keygen → sign → verify), the
re-seal-breaks-the-signature property, ``--require-signed``, and the
libsodium cross-check need the ``sign`` extra and skip cleanly without it.
The verify path is asserted to pull no ``nacl``.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from binascii import unhexlify
from pathlib import Path

import pytest

from tessera.bundle.ed25519 import verify as ed_verify
from tessera.bundle.emit import build_bundle, bundle_bytes
from tessera.bundle.format import seal
from tessera.bundle.verify import BundleFormatError, verify_bundle

_HAVE_NACL = importlib.util.find_spec("nacl") is not None
_needs_sign = pytest.mark.skipif(not _HAVE_NACL, reason="needs the 'sign' extra")

_Q = "Compare Müller Logistik and Nordwind Logistik totals."


# --- the pure-Python verifier (no extra) --------------------------------------------

# RFC 8032 §7.1 TEST 1-3: (public key, message, signature).
_RFC_VECTORS = [
    (
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        "",
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8"
        "821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
    ),
    (
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        "72",
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085a"
        "c1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
    ),
    (
        "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
        "af82",
        "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff"
        "9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a",
    ),
]


@pytest.mark.parametrize("pk_hex,msg_hex,sig_hex", _RFC_VECTORS)
def test_rfc8032_vectors_verify(pk_hex: str, msg_hex: str, sig_hex: str) -> None:
    pk, msg, sig = unhexlify(pk_hex), unhexlify(msg_hex), unhexlify(sig_hex)
    assert ed_verify(pk, msg, sig)


@pytest.mark.parametrize("pk_hex,msg_hex,sig_hex", _RFC_VECTORS)
def test_rfc8032_vectors_reject_tampering(
    pk_hex: str, msg_hex: str, sig_hex: str
) -> None:
    pk, msg, sig = unhexlify(pk_hex), unhexlify(msg_hex), unhexlify(sig_hex)
    flipped = bytearray(sig)
    flipped[0] ^= 1
    assert not ed_verify(pk, msg, bytes(flipped))  # bad signature
    assert not ed_verify(pk, msg + b"x", sig)  # wrong message
    bad_key = bytearray(pk)
    bad_key[0] ^= 1
    assert not ed_verify(bytes(bad_key), msg, sig)  # wrong key


def test_verify_never_raises_on_malformed_input() -> None:
    assert not ed_verify(b"", b"m", b"")
    assert not ed_verify(b"\x00" * 32, b"m", b"\x00" * 63)  # wrong sig length
    assert not ed_verify(b"\xff" * 32, b"m", b"\x00" * 64)  # off-curve key


# --- signing round-trip (needs the extra) -------------------------------------------


@_needs_sign
def test_keygen_sign_verify_round_trip(tmp_path: Path) -> None:
    from tessera.bundle.signing import generate_keypair, sign_bundle

    key = tmp_path / "k.key"
    public_hex = generate_keypair(key)
    assert (tmp_path / "k.key.pub").read_text().strip() == public_hex
    assert oct(key.stat().st_mode & 0o777) == "0o600"

    signed = sign_bundle(build_bundle("business", _Q), key)
    report = verify_bundle(json.loads(json.dumps(signed)))
    assert report.signature_status == "SIGNED"
    assert report.signature_public_key == public_hex
    assert report.signature_problems == ()
    assert report.exit_code == 0


@_needs_sign
def test_keygen_refuses_to_overwrite(tmp_path: Path) -> None:
    from tessera.bundle.signing import generate_keypair

    key = tmp_path / "k.key"
    generate_keypair(key)
    with pytest.raises(FileExistsError):
        generate_keypair(key)


@_needs_sign
def test_reseal_breaks_the_signature(tmp_path: Path) -> None:
    """The origin binding Milestone 20 lacked: a content tamperer can re-seal
    (recompute manifest + root) — but the signature is over a root they cannot
    reproduce without the key, so it fails, exit 4."""
    from tessera.bundle.signing import generate_keypair, sign_bundle

    key = tmp_path / "k.key"
    generate_keypair(key)
    signed = sign_bundle(build_bundle("business", _Q), key)

    tampered = copy.deepcopy(signed)
    cited = tampered["result"]["claims"][0]["support"][0]["id"]  # type: ignore[index]
    for node in tampered["evidence_closure"]["graph"]["nodes"]:  # type: ignore[index]
        if node["record"]["id"] == cited:
            attrs = dict(node["attributes"])
            old = attrs["net_amount"]
            new = str(int(float(old)) + 30000) + ".00"
            node["attributes"] = [
                [k, new if k == "net_amount" else v] for k, v in node["attributes"]
            ]
            node["record"]["text"] = node["record"]["text"].replace(old, new)
            break
    sig = tampered.pop("signature")
    del tampered["integrity"]
    resealed = seal(tampered)
    resealed["signature"] = sig  # keep the old signature over the old root

    report = verify_bundle(resealed)
    assert report.integrity_problems == ()  # root recomputed fine
    assert report.signature_problems  # but the signature is over the old root
    assert report.exit_code == 4 and report.verdict == "TAMPERED"


@_needs_sign
def test_cross_check_libsodium_signature_verifies_pure_python(tmp_path: Path) -> None:
    """A signature produced by libsodium (PyNaCl) verifies under our
    pure-Python implementation — the two agree."""
    from nacl.signing import SigningKey

    sk = SigningKey.generate()
    message = b"tessera cross-check message"
    signed = sk.sign(message)
    assert ed_verify(bytes(sk.verify_key), message, signed.signature)


# --- policy + unsigned behaviour (no extra) -----------------------------------------


def test_unsigned_bundle_is_labeled_and_passes() -> None:
    report = verify_bundle(json.loads(bundle_bytes(build_bundle("devex", _Q))))
    assert report.signature_status == "UNSIGNED"
    assert report.signature_problems == ()
    assert report.exit_code == 0  # unsigned is not a failure by default


def test_require_signed_fails_an_unsigned_bundle() -> None:
    report = verify_bundle(
        json.loads(bundle_bytes(build_bundle("devex", _Q))), require_signed=True
    )
    assert report.exit_code == 4
    assert any("unsigned" in p for p in report.signature_problems)


def test_malformed_signature_section_is_an_envelope_error() -> None:
    bundle = json.loads(bundle_bytes(build_bundle("business", _Q)))
    bundle["signature"] = {"algorithm": "rsa", "public_key": "00", "signature": "00"}
    with pytest.raises(BundleFormatError, match="algorithm"):
        verify_bundle(bundle)


def test_wrong_length_signature_is_an_envelope_error() -> None:
    bundle = json.loads(bundle_bytes(build_bundle("business", _Q)))
    bundle["signature"] = {
        "algorithm": "ed25519",
        "public_key": "ab",  # too short
        "signature": "cd" * 64,
    }
    with pytest.raises(BundleFormatError, match="length"):
        verify_bundle(bundle)


def test_verify_path_pulls_no_nacl() -> None:
    """The stdlib-only promise for verification: importing the whole verify
    surface (and the pure-Python ed25519) must not pull the 'sign' extra."""
    script = (
        "import sys\n"
        "import tessera.bundle.cli\n"
        "import tessera.bundle.verify\n"
        "import tessera.bundle.ed25519\n"
        "assert 'nacl' not in sys.modules, 'verify path pulled nacl'\n"
    )
    subprocess.run([sys.executable, "-c", script], check=True)


# --- the CLI (needs the extra for signing; verify half runs anywhere) ---------------


@_needs_sign
def test_cli_keygen_sign_verify_via_front_door(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from tessera.cli import main as front_door

    key = tmp_path / "k.key"
    out = tmp_path / "signed.tsb"
    assert front_door(["bundle", "keygen", "--key", str(key)]) == 0
    assert "public key:" in capsys.readouterr().out

    code = front_door(
        [
            "bundle",
            _Q,
            "--domain",
            "business",
            "-o",
            str(out),
            "--sign",
            "--key",
            str(key),
        ]
    )
    assert code == 0
    assert "signed:  key" in capsys.readouterr().out

    assert front_door(["verify", str(out)]) == 0
    assert "signature: valid" in capsys.readouterr().out

    assert front_door(["verify", str(out), "--require-signed"]) == 0


def test_cli_require_signed_rejects_unsigned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from tessera.bundle.cli import main as bundle_cli
    from tessera.bundle.cli import verify_main

    out = tmp_path / "unsigned.tsb"
    assert bundle_cli([_Q, "--domain", "business", "-o", str(out)]) == 0
    capsys.readouterr()
    assert verify_main([str(out), "--require-signed"]) == 4
    assert "signature: BROKEN" in capsys.readouterr().out


def test_cli_sign_without_key_is_a_clean_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--sign with no key present is a clean exit 2, never a traceback."""
    from tessera.bundle.cli import main as bundle_cli

    out = tmp_path / "x.tsb"
    missing = tmp_path / "nope.key"
    code = bundle_cli(
        [_Q, "--domain", "business", "-o", str(out), "--sign", "--key", str(missing)]
    )
    assert code == 2
    assert "error:" in capsys.readouterr().err
