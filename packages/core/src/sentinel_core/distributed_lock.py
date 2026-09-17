import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.models import EngineNode, CryptographicLease

class EphemeralNodeIdentity:
    """
    Represents the in-memory cryptographic identity of a running Sentinel Engine.
    Destroyed when the process terminates.
    """
    def __init__(self):
        self.node_id = str(uuid4())
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key_pem = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        
    def sign_lease_payload(self, resource_id: str, expires_at: datetime) -> str:
        payload = f"{resource_id}:{self.node_id}:{int(expires_at.timestamp())}".encode("utf-8")
        signature = self._private_key.sign(payload)
        return signature.hex()
        
    def verify_lease_signature(self, public_key_pem: str, resource_id: str, owner_node_id: str, expires_at: datetime, signature_hex: str) -> bool:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        payload = f"{resource_id}:{owner_node_id}:{int(expires_at.timestamp())}".encode("utf-8")
        try:
            public_key.verify(bytes.fromhex(signature_hex), payload)
            return True
        except InvalidSignature:
            return False


async def register_engine_node(session: AsyncSession, identity: EphemeralNodeIdentity) -> EngineNode:
    """
    Registers the engine node in the database, allowing other nodes to verify its locks.
    """
    node = EngineNode(
        id=identity.node_id,
        public_key=identity.public_key_pem,
        status="active",
        last_heartbeat=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    session.add(node)
    await session.flush()
    return node


async def acquire_cryptographic_lease(
    session: AsyncSession, 
    identity: EphemeralNodeIdentity, 
    resource_id: str, 
    duration_seconds: int = 60
) -> CryptographicLease | None:
    """
    Securely acquires a distributed lock. Generates a mathematical proof using the node's private key.
    If the lock is held, it safely fails.
    """
    # 1. Ensure the lease row exists
    lease = (await session.execute(
        select(CryptographicLease).where(CryptographicLease.resource_id == resource_id)
    )).scalar_one_or_none()
    
    if not lease:
        lease = CryptographicLease(
            resource_id=resource_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(lease)
        await session.flush()
        
    now = datetime.now(timezone.utc)
    
    # 2. Check if currently locked
    if lease.owner_node_id and lease.expires_at and lease.expires_at > now:
        # Check if the lock owner is still mathematically valid (Anti-tamper check)
        if lease.cryptographic_proof:
            owner_node = (await session.execute(
                select(EngineNode).where(EngineNode.id == lease.owner_node_id)
            )).scalar_one_or_none()
            
            if owner_node:
                is_valid = identity.verify_lease_signature(
                    owner_node.public_key, 
                    lease.resource_id, 
                    lease.owner_node_id, 
                    lease.expires_at, 
                    lease.cryptographic_proof
                )
                if not is_valid:
                    raise ValueError(f"CRITICAL SECURITY ALERT: Lease {resource_id} has a forged signature!")
                    
        if lease.owner_node_id != identity.node_id:
            return None # Locked by someone else
            
    # 3. Claim the lock
    expires_at = now + timedelta(seconds=duration_seconds)
    signature = identity.sign_lease_payload(resource_id, expires_at)
    
    lease.owner_node_id = identity.node_id
    lease.expires_at = expires_at
    lease.cryptographic_proof = signature
    lease.updated_at = now
    
    await session.flush()
    return lease
