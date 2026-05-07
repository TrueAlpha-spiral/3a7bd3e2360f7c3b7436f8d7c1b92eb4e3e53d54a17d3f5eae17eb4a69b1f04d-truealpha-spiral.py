"""SDF↔TAS civic transaction interface for sovereign individuals."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import secrets
from typing import Any, Dict, List, Tuple

from tas_phase0_microkernel import (
    ALLOW_STATUS,
    DENY_STATUS,
    ActionProposal,
    Phase0Manifest,
    VerificationPolicy,
    boot_microkernel,
    digest_payload,
    guard_accepts_token,
    sign_payload,
    verify_action,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SovereignIdentity:
    alias: str
    sovereign_id: str
    public_key: str
    private_key: str


@dataclass(frozen=True)
class EpistemicCapsule:
    owner_id: str
    claims: Tuple[str, ...]
    sources: Tuple[str, ...]
    attestations: Tuple[str, ...]
    consent_scope: str
    revocation_policy: str

    def payload(self) -> Dict[str, Any]:
        return asdict(self)

    def capsule_hash(self) -> str:
        return digest_payload(self.payload())


@dataclass(frozen=True)
class CursiveComputationIntent:
    intent_id: str
    action: str
    policy_scope: str
    record_hash: str
    anchor_hash: str
    nonce: str
    counter: int
    attestation_digest: str
    policy_hash: str
    previous_receipt_hash: str
    snapshot_id: str


class SDFRegistryAPI:
    """Institutional witness layer: schema gates + immutable receipt ledger."""

    def __init__(self, witness_signing_key: str):
        self._witness_signing_key = witness_signing_key
        self.identity_registry: Dict[str, Dict[str, Any]] = {}
        self.ledger: List[Dict[str, Any]] = []
        self._sequence = 0

    def register_identity(self, identity: SovereignIdentity, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        self.identity_registry[identity.sovereign_id] = {
            "alias": identity.alias,
            "sovereign_id": identity.sovereign_id,
            "public_key": identity.public_key,
            "metadata": metadata or {},
        }
        return dict(self.identity_registry[identity.sovereign_id])

    def notarize_capsule(self, capsule: EpistemicCapsule) -> Dict[str, Any]:
        if not capsule.claims:
            raise ValueError("capsule missing claims")
        if not capsule.sources:
            raise ValueError("capsule missing sources")
        if not capsule.attestations:
            raise ValueError("capsule missing attestations")
        if not capsule.consent_scope.strip():
            raise ValueError("capsule missing consent_scope")
        if not capsule.revocation_policy.strip():
            raise ValueError("capsule missing revocation_policy")

        self._sequence += 1
        unsigned = {
            "record_id": f"record-{self._sequence:06d}",
            "record_hash": capsule.capsule_hash(),
            "owner_id": capsule.owner_id,
            "ledger_tx": f"tx-{self._sequence:06d}",
            "timestamp_utc": _utc_timestamp(),
            "status": "WITNESSED",
            "event": "CAPSULE_NOTARIZED",
        }
        receipt = dict(unsigned)
        receipt["witness_signature"] = sign_payload(unsigned, self._witness_signing_key)
        self.ledger.append(receipt)
        return receipt

    def append_execution_record(
        self,
        record_id: str,
        execution_trace_hash: str,
        previous_receipt_hash: str,
        status: str,
    ) -> Dict[str, Any]:
        self._sequence += 1
        unsigned = {
            "record_id": record_id,
            "ledger_tx": f"tx-{self._sequence:06d}",
            "event": "EXECUTION_RECORDED",
            "status": status,
            "execution_trace_hash": execution_trace_hash,
            "previous_receipt_hash": previous_receipt_hash,
            "timestamp_utc": _utc_timestamp(),
        }
        entry = dict(unsigned)
        entry["witness_signature"] = sign_payload(unsigned, self._witness_signing_key)
        self.ledger.append(entry)
        return entry

    def query_record(self, record_id: str) -> List[Dict[str, Any]]:
        return [entry for entry in self.ledger if entry.get("record_id") == record_id]


class TASAdmissibilityGateway:
    """Computational enforcement bridge: Phase 0 bind + policy verification."""

    def __init__(self, policy: VerificationPolicy, verifier_signing_key: str):
        self.policy = policy
        self.verifier_signing_key = verifier_signing_key

    def boot_phase0(self, manifest: Phase0Manifest) -> Dict[str, Any]:
        receipt = boot_microkernel(manifest)
        if "anchor_hash" not in receipt:
            raise ValueError(f"phase0 boot refused: {receipt.get('reason', 'unknown')}")
        return receipt

    def bind_record_to_anchor(self, record_hash: str, anchor_hash: str) -> Dict[str, Any]:
        payload = {
            "status": "ADMISSIBILITY_BRIDGE_ESTABLISHED",
            "bridge": "△ _ ⁻ = ≡ ▲",
            "record_hash": record_hash,
            "anchor_hash": anchor_hash,
            "timestamp_utc": _utc_timestamp(),
        }
        payload["binding_hash"] = digest_payload(payload)
        receipt = dict(payload)
        receipt["signature"] = sign_payload(payload, self.verifier_signing_key)
        return receipt

    def evaluate_intent(self, intent: CursiveComputationIntent) -> Dict[str, Any]:
        if not intent.record_hash or not intent.anchor_hash:
            refusal_payload = {
                "status": DENY_STATUS,
                "reason": "missing record_hash or anchor_hash",
                "intent_id": intent.intent_id,
                "record_hash": intent.record_hash,
                "anchor_hash": intent.anchor_hash,
            }
            refusal_payload["receipt_hash"] = digest_payload(refusal_payload)
            refusal = dict(refusal_payload)
            refusal["signature"] = sign_payload(refusal_payload, self.verifier_signing_key)
            return refusal

        proposal = ActionProposal(
            proposal_id=intent.intent_id,
            action=intent.action,
            nonce=intent.nonce,
            counter=intent.counter,
            attestation_digest=intent.attestation_digest,
            policy_hash=intent.policy_hash,
            previous_receipt_hash=intent.previous_receipt_hash,
            snapshot_id=intent.snapshot_id,
        )
        verification_receipt = verify_action(proposal, self.policy, self.verifier_signing_key)

        payload = {
            "intent_id": intent.intent_id,
            "policy_scope": intent.policy_scope,
            "status": verification_receipt["status"],
            "record_hash": intent.record_hash,
            "anchor_hash": intent.anchor_hash,
            "verification_receipt": verification_receipt,
        }
        payload["gateway_receipt_hash"] = digest_payload(payload)
        gateway_receipt = dict(payload)
        gateway_receipt["signature"] = sign_payload(payload, self.verifier_signing_key)
        return gateway_receipt


class ExternalActuatorGuard:
    """Independent guard that only executes with a valid one-shot token."""

    def __init__(self, verifier_signing_key: str):
        self.verifier_signing_key = verifier_signing_key
        self._used_counters: set[int] = set()

    def execute(self, gateway_receipt: Dict[str, Any]) -> Dict[str, Any]:
        verification_receipt = gateway_receipt.get("verification_receipt", {})
        token = verification_receipt.get("actuation_token")

        allowed = guard_accepts_token(token, self.verifier_signing_key, self._used_counters)
        status = "EXECUTED" if allowed else "REFUSED"

        trace_payload = {
            "intent_id": gateway_receipt.get("intent_id"),
            "status": status,
            "record_hash": gateway_receipt.get("record_hash"),
            "anchor_hash": gateway_receipt.get("anchor_hash"),
            "verification_receipt_hash": verification_receipt.get("receipt_hash"),
            "result_digest": digest_payload(
                {
                    "intent_id": gateway_receipt.get("intent_id"),
                    "status": status,
                }
            ),
            "timestamp_utc": _utc_timestamp(),
        }
        trace_payload["trace_hash"] = digest_payload(trace_payload)
        trace = dict(trace_payload)
        trace["signature"] = sign_payload(trace_payload, self.verifier_signing_key)
        return trace


class CitizenPortal:
    """Single-user interface for identity, capsule lodging, and first computation."""

    def __init__(self, registry: SDFRegistryAPI, gateway: TASAdmissibilityGateway, guard: ExternalActuatorGuard):
        self.registry = registry
        self.gateway = gateway
        self.guard = guard

    def create_identity(self, alias: str) -> SovereignIdentity:
        private_key = secrets.token_hex(32)
        public_key = sha256(private_key.encode("utf-8")).hexdigest()
        sovereign_id = f"did:tas:{sha256(f'{alias}:{public_key}'.encode('utf-8')).hexdigest()[:24]}"
        return SovereignIdentity(alias=alias, sovereign_id=sovereign_id, public_key=public_key, private_key=private_key)

    def package_epistemology(
        self,
        owner_id: str,
        claims: List[str],
        sources: List[str],
        attestations: List[str],
        consent_scope: str,
        revocation_policy: str,
    ) -> EpistemicCapsule:
        return EpistemicCapsule(
            owner_id=owner_id,
            claims=tuple(claims),
            sources=tuple(sources),
            attestations=tuple(attestations),
            consent_scope=consent_scope,
            revocation_policy=revocation_policy,
        )

    def lodge_epistemology(self, capsule: EpistemicCapsule) -> Dict[str, Any]:
        return self.registry.notarize_capsule(capsule)

    def initiate_first_cursive_computation(
        self,
        manifest: Phase0Manifest,
        record_receipt: Dict[str, Any],
        action: str,
        policy_scope: str,
        attestation_digest: str,
        policy_hash: str,
    ) -> Dict[str, Any]:
        timeline = ["submitted", "witnessed"]
        boot_receipt = self.gateway.boot_phase0(manifest)
        binding_receipt = self.gateway.bind_record_to_anchor(
            record_hash=record_receipt["record_hash"],
            anchor_hash=boot_receipt["anchor_hash"],
        )
        timeline.append("admissible")

        intent = CursiveComputationIntent(
            intent_id=f"intent-{secrets.token_hex(8)}",
            action=action,
            policy_scope=policy_scope,
            record_hash=record_receipt["record_hash"],
            anchor_hash=boot_receipt["anchor_hash"],
            nonce=secrets.token_hex(8),
            counter=1,
            attestation_digest=attestation_digest,
            policy_hash=policy_hash,
            previous_receipt_hash=record_receipt["ledger_tx"],
            snapshot_id=record_receipt["record_id"],
        )
        gateway_receipt = self.gateway.evaluate_intent(intent)
        execution_trace = self.guard.execute(gateway_receipt)

        execution_ledger_receipt = self.registry.append_execution_record(
            record_id=record_receipt["record_id"],
            execution_trace_hash=execution_trace["trace_hash"],
            previous_receipt_hash=gateway_receipt.get("gateway_receipt_hash", gateway_receipt.get("receipt_hash", "")),
            status=execution_trace["status"],
        )

        timeline.append("executed" if execution_trace["status"] == "EXECUTED" else "refused")
        return {
            "timeline": timeline,
            "record_receipt": record_receipt,
            "boot_receipt": boot_receipt,
            "binding_receipt": binding_receipt,
            "gateway_receipt": gateway_receipt,
            "execution_trace": execution_trace,
            "execution_ledger_receipt": execution_ledger_receipt,
        }

    def view_timeline(self, record_id: str) -> List[Dict[str, Any]]:
        return self.registry.query_record(record_id)


class PublicVerifier:
    """Independent verifier that replays hash/signature lineage."""

    def __init__(self, witness_signing_key: str, verifier_signing_key: str):
        self.witness_signing_key = witness_signing_key
        self.verifier_signing_key = verifier_signing_key

    @staticmethod
    def _verify_signature(signed_payload: Dict[str, Any], signature_field: str, signing_key: str) -> bool:
        payload = dict(signed_payload)
        signature = payload.pop(signature_field, None)
        if signature is None:
            return False
        return signature == sign_payload(payload, signing_key)

    def verify_transaction(self, capsule: EpistemicCapsule, transaction: Dict[str, Any]) -> bool:
        record_receipt = transaction["record_receipt"]
        boot_receipt = transaction["boot_receipt"]
        binding_receipt = transaction["binding_receipt"]
        gateway_receipt = transaction["gateway_receipt"]
        execution_trace = transaction["execution_trace"]
        execution_ledger_receipt = transaction["execution_ledger_receipt"]

        if capsule.capsule_hash() != record_receipt.get("record_hash"):
            return False
        if not self._verify_signature(record_receipt, "witness_signature", self.witness_signing_key):
            return False
        if not self._verify_signature(binding_receipt, "signature", self.verifier_signing_key):
            return False
        if binding_receipt.get("record_hash") != record_receipt.get("record_hash"):
            return False
        if binding_receipt.get("anchor_hash") != boot_receipt.get("anchor_hash"):
            return False

        if gateway_receipt.get("status") in (ALLOW_STATUS, DENY_STATUS):
            if not self._verify_signature(gateway_receipt, "signature", self.verifier_signing_key):
                return False
            verification_receipt = gateway_receipt.get("verification_receipt")
            if verification_receipt and not self._verify_signature(
                verification_receipt, "signature", self.verifier_signing_key
            ):
                return False
            if gateway_receipt.get("record_hash") != record_receipt.get("record_hash"):
                return False
            if gateway_receipt.get("anchor_hash") != boot_receipt.get("anchor_hash"):
                return False
        else:
            return False

        if not self._verify_signature(execution_trace, "signature", self.verifier_signing_key):
            return False
        if not self._verify_signature(execution_ledger_receipt, "witness_signature", self.witness_signing_key):
            return False
        if execution_ledger_receipt.get("record_id") != record_receipt.get("record_id"):
            return False
        if execution_ledger_receipt.get("execution_trace_hash") != execution_trace.get("trace_hash"):
            return False
        return True
