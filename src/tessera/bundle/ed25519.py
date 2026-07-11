"""Pure-Python Ed25519 signature verification (RFC 8032), verify-only.

Spec 0135 / ADR 0032. This exists so ``tessera verify`` stays **stdlib-only**
on a clean clone: a stranger checks a signed bundle's origin with nothing but
the standard library. Signing lives in :mod:`tessera.bundle.signing` behind
the optional ``sign`` extra (libsodium via PyNaCl); this module never touches
a secret key — it only verifies.

The implementation follows RFC 8032 §5.1 (Ed25519, SHA-512, curve25519 in
Edwards form) and is pinned against the RFC 8032 §7.1 test vectors and,
when the ``sign`` extra is installed, cross-checked against libsodium-produced
signatures. Correctness — not speed — is the goal: a single verification is a
few tens of milliseconds, which is irrelevant for a one-shot audit check.
"""

from __future__ import annotations

import hashlib

# Curve constants (RFC 8032 §5.1).
_P = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
_I = pow(2, (_P - 1) // 4, _P)  # sqrt(-1) mod p
# Base point B (RFC 8032 §5.1): y = 4/5, x the positive root.
_BY = (4 * pow(5, _P - 2, _P)) % _P


def _recover_x(y: int, sign: int) -> int | None:
    """The x-coordinate for a given y and sign bit (RFC 8032 §5.1.3), or
    ``None`` when no square root exists (point not on the curve)."""
    if y >= _P:
        return None
    u = (y * y - 1) % _P
    v = (_D * y * y + 1) % _P
    # x = u * v^3 * (u * v^7)^((p-5)/8)
    v3 = (v * v * v) % _P
    v7 = (v3 * v3 * v) % _P
    x = (u * v3 * pow(u * v7, (_P - 5) // 8, _P)) % _P
    vx2 = (v * x * x) % _P
    if vx2 == u % _P:
        pass
    elif vx2 == (-u) % _P:
        x = (x * _I) % _P
    else:
        return None
    if x == 0 and sign:
        return None
    if x & 1 != sign:
        x = _P - x
    return x


# Edwards-curve point arithmetic in extended homogeneous coordinates
# (X, Y, Z, T) with x = X/Z, y = Y/Z, x*y = T/Z (RFC 8032 §5.1.4).
_Point = tuple[int, int, int, int]


def _point_add(p: _Point, q: _Point) -> _Point:
    x1, y1, z1, t1 = p
    x2, y2, z2, t2 = q
    a = ((y1 - x1) * (y2 - x2)) % _P
    b = ((y1 + x1) * (y2 + x2)) % _P
    c = (t1 * 2 * _D * t2) % _P
    dd = (z1 * 2 * z2) % _P
    e = (b - a) % _P
    f = (dd - c) % _P
    g = (dd + c) % _P
    h = (b + a) % _P
    return (e * f) % _P, (g * h) % _P, (f * g) % _P, (e * h) % _P


def _point_mul(scalar: int, point: _Point) -> _Point:
    result: _Point = (0, 1, 1, 0)  # neutral element
    while scalar > 0:
        if scalar & 1:
            result = _point_add(result, point)
        point = _point_add(point, point)
        scalar >>= 1
    return result


def _point_equal(p: _Point, q: _Point) -> bool:
    x1, y1, z1, _ = p
    x2, y2, z2, _ = q
    if (x1 * z2 - x2 * z1) % _P != 0:
        return False
    return (y1 * z2 - y2 * z1) % _P == 0


def _base_point() -> _Point:
    bx = _recover_x(_BY, 0)
    assert bx is not None  # the base point is on the curve by construction
    return (bx, _BY, 1, (bx * _BY) % _P)


def _decompress(data: bytes) -> _Point | None:
    """Decode a 32-byte compressed point to (X, Y, Z, T), or ``None`` when it
    is not a valid curve point."""
    if len(data) != 32:
        return None
    y = int.from_bytes(data, "little")
    sign = (y >> 255) & 1
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, (x * y) % _P)


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """True iff ``signature`` is a valid Ed25519 signature of ``message`` under
    ``public_key`` (RFC 8032 §5.1.7). All-bytes API; never raises on malformed
    input — a wrong length or an off-curve key simply returns ``False``."""
    if len(public_key) != 32 or len(signature) != 64:
        return False
    a_point = _decompress(public_key)
    if a_point is None:
        return False
    r_bytes = signature[:32]
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:  # S must be reduced (RFC 8032: reject non-canonical S)
        return False
    r_point = _decompress(r_bytes)
    if r_point is None:
        return False
    digest = hashlib.sha512(r_bytes + public_key + message).digest()
    k = int.from_bytes(digest, "little") % _L
    # Check [S]B == R + [k]A.
    sb = _point_mul(s, _base_point())
    ka = _point_mul(k, a_point)
    rhs = _point_add(r_point, ka)
    return _point_equal(sb, rhs)
