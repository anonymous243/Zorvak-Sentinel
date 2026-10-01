from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from sentinel_core.authorization import ActionRequest
from sentinel_core.principals import AuthenticatedPrincipal

class RequestReplayError(ValueError):
    """Raised when a valid signed request is submitted more than once."""
    pass

def canonicalize_request(
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    timestamp: datetime,
) -> bytes:
    """
    Produce the canonical byte representation that an agent signs.

    The authenticated principal supplies tenant_id and agent_id.
    Caller-controlled context is deliberately excluded from the signed
    security identity binding for now.
    """
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")

    timestamp_utc = timestamp.astimezone(timezone.utc)

    payload = {
        "tenant_id": principal.tenant_id,
        "agent_id": principal.agent_id,
        "request_id": str(request.request_id),
        "tool_id": request.tool_id,
        "action": request.action,
        "resource": request.resource,
        "timestamp": timestamp_utc.isoformat(),
    }
    if getattr(request, "delegation_id", None):
        payload["delegation_id"] = str(request.delegation_id)

    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def compute_request_fingerprint(
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    timestamp: datetime,
) -> str:
    """
    Generate an authoritative canonical fingerprint for idempotency.
    """
    canonical_bytes = canonicalize_request(request, principal, timestamp)
    return hashlib.sha256(canonical_bytes).hexdigest()


def generate_signing_keypair() -> tuple[str, str]:
    """
    Generate an Ed25519 keypair.

    Returns:
        (private_key_pem, public_key_pem)

    Private key material is returned only to the caller and must never
    be persisted by SENTINEL.
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    return private_pem, public_pem


def sign_request(
    private_key_pem: str,
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    timestamp: datetime,
) -> str:
    """
    Sign the canonical request representation using Ed25519.

    Returns the signature encoded as URL-safe base64 text.
    """
    import base64

    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("ascii"),
            password=None,
        )
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid Ed25519 private key") from exc

    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Private key is not an Ed25519 key")

    payload = canonicalize_request(request, principal, timestamp)
    signature = private_key.sign(payload)

    return base64.urlsafe_b64encode(signature).decode("ascii")


def verify_request_signature_detailed(
    public_key_pem: str,
    signature: str,
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    timestamp: datetime,
) -> tuple[bool, str | None]:
    """
    Verify an Ed25519 signature over the canonical request, returning
    (is_valid, failure_reason).
    """
    import base64

    if not signature or not signature.strip():
        return False, "missing_signature"

    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode("ascii"),
        )
        if not isinstance(public_key, Ed25519PublicKey):
            return False, "invalid_signing_key_type"
    except Exception:
        return False, "malformed_signing_key"

    try:
        signature_bytes = base64.urlsafe_b64decode(
            signature.encode("ascii"),
        )
        if len(signature_bytes) != 64:
            return False, "malformed_signature"
    except Exception:
        return False, "malformed_signature"

    try:
        payload = canonicalize_request(
            request,
            principal,
            timestamp,
        )
        public_key.verify(signature_bytes, payload)
        return True, None
    except InvalidSignature:
        return False, "invalid_signature"
    except Exception:
        return False, "invalid_signature"


def verify_request_signature(
    public_key_pem: str,
    signature: str,
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    timestamp: datetime,
) -> bool:
    """
    Verify an Ed25519 signature over the canonical request.

    Any malformed key, malformed signature, or invalid signature fails
    closed and returns False.
    """
    valid, _ = verify_request_signature_detailed(
        public_key_pem=public_key_pem,
        signature=signature,
        request=request,
        principal=principal,
        timestamp=timestamp,
    )
    return valid

