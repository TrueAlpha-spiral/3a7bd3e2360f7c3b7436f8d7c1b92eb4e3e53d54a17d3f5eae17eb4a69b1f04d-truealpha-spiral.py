import unittest

from sdf_tas_interface import (
    CitizenPortal,
    ExternalActuatorGuard,
    PublicVerifier,
    SDFRegistryAPI,
    TASAdmissibilityGateway,
)
from tas_phase0_microkernel import ALLOW_STATUS, DENY_STATUS, VerificationPolicy, default_manifest


class TestSDFTASCivicInterface(unittest.TestCase):
    def setUp(self):
        # Test-only static signing keys. Production must use securely generated
        # key material and hardened storage.
        self.witness_key = "sdf-witness-key"
        self.verifier_key = "tas-verifier-key"
        self.policy = VerificationPolicy(
            allowed_actions=("OPEN_RELAY",),
            expected_attestation_digest="attested",
            expected_policy_hash="policy123",
        )
        self.registry = SDFRegistryAPI(witness_signing_key=self.witness_key)
        self.gateway = TASAdmissibilityGateway(policy=self.policy, verifier_signing_key=self.verifier_key)
        self.guard = ExternalActuatorGuard(verifier_signing_key=self.verifier_key)
        self.portal = CitizenPortal(self.registry, self.gateway, self.guard)
        self.verifier = PublicVerifier(self.witness_key, self.verifier_key)

    def test_full_seven_step_transaction_success(self):
        identity = self.portal.create_identity("Ada Sovereign")
        self.registry.register_identity(identity, metadata={"jurisdiction": "civic"})

        self.assertIn(identity.sovereign_id, self.registry.identity_registry)
        self.assertNotIn("private_key", self.registry.identity_registry[identity.sovereign_id])
        self.assertTrue(self.portal.get_local_private_key(identity.sovereign_id))

        capsule = self.portal.package_epistemology(
            owner_id=identity.sovereign_id,
            claims=["Claim 1"],
            sources=["Source A"],
            attestations=["Attestation alpha"],
            consent_scope="public verification only",
            revocation_policy="prospective only",
        )
        record_receipt = self.portal.lodge_epistemology(capsule)
        tx = self.portal.initiate_first_cursive_computation(
            manifest=default_manifest(),
            record_receipt=record_receipt,
            action="OPEN_RELAY",
            policy_scope="first-cursive",
            attestation_digest="attested",
            policy_hash="policy123",
        )

        self.assertEqual(tx["timeline"], ["submitted", "witnessed", "admissible", "executed"])
        self.assertEqual(tx["gateway_receipt"]["status"], ALLOW_STATUS)
        self.assertEqual(tx["execution_trace"]["status"], "EXECUTED")
        self.assertTrue(self.verifier.verify_transaction(capsule, tx))

    def test_refusal_path_is_witnessed_and_verifiable(self):
        identity = self.portal.create_identity("Byron Sovereign")
        self.registry.register_identity(identity)
        capsule = self.portal.package_epistemology(
            owner_id=identity.sovereign_id,
            claims=["Claim 2"],
            sources=["Source B"],
            attestations=["Attestation beta"],
            consent_scope="policy scoped",
            revocation_policy="immediate",
        )
        record_receipt = self.portal.lodge_epistemology(capsule)
        tx = self.portal.initiate_first_cursive_computation(
            manifest=default_manifest(),
            record_receipt=record_receipt,
            action="DELETE_ALL",
            policy_scope="first-cursive",
            attestation_digest="attested",
            policy_hash="policy123",
        )

        self.assertEqual(tx["gateway_receipt"]["status"], DENY_STATUS)
        self.assertEqual(tx["execution_trace"]["status"], "REFUSED")
        self.assertEqual(tx["timeline"][-1], "refused")
        self.assertTrue(self.verifier.verify_transaction(capsule, tx))

    def test_verify_transaction_performance_lock(self):
        """
        The Invariant: Optimization AND Safety = True.
        This Sentient Lock test verifies that deferring expensive signature validation
        in verify_transaction until after simple logical checks are evaluated
        yields a significant performance speedup for invalid/rejected transactions.
        """
        import timeit
        import copy
        import types

        identity = self.portal.create_identity("SpeedLock Sovereign")
        self.registry.register_identity(identity)
        capsule = self.portal.package_epistemology(
            owner_id=identity.sovereign_id,
            claims=["Speed Claim"],
            sources=["Speed Source"],
            attestations=["Speed Attestation"],
            consent_scope="testing",
            revocation_policy="none",
        )
        record_receipt = self.portal.lodge_epistemology(capsule)
        valid_tx = self.portal.initiate_first_cursive_computation(
            manifest=default_manifest(),
            record_receipt=record_receipt,
            action="OPEN_RELAY",
            policy_scope="first-cursive",
            attestation_digest="attested",
            policy_hash="policy123",
        )

        # Create an invalid transaction (e.g., mismatched record_hash in binding_receipt)
        # to trigger early return.
        invalid_tx = copy.deepcopy(valid_tx)
        invalid_tx["binding_receipt"]["record_hash"] = "invalid_hash"

        # Define the unoptimized logic (signatures first)
        def unoptimized_verify(self_verifier, capsule, transaction) -> bool:
            record_receipt = transaction["record_receipt"]
            boot_receipt = transaction["boot_receipt"]
            binding_receipt = transaction["binding_receipt"]
            gateway_receipt = transaction["gateway_receipt"]
            execution_trace = transaction["execution_trace"]
            execution_ledger_receipt = transaction["execution_ledger_receipt"]

            if capsule.capsule_hash() != record_receipt.get("record_hash"):
                return False
            if not self_verifier._verify_signature(record_receipt, "witness_signature", self_verifier.witness_signing_key):
                return False
            if not self_verifier._verify_signature(binding_receipt, "signature", self_verifier.verifier_signing_key):
                return False
            if binding_receipt.get("record_hash") != record_receipt.get("record_hash"):
                return False
            if binding_receipt.get("anchor_hash") != boot_receipt.get("anchor_hash"):
                return False

            if gateway_receipt.get("status") in (ALLOW_STATUS, DENY_STATUS):
                if not self_verifier._verify_signature(gateway_receipt, "signature", self_verifier.verifier_signing_key):
                    return False
                verification_receipt = gateway_receipt.get("verification_receipt")
                if verification_receipt and not self_verifier._verify_signature(
                    verification_receipt, "signature", self_verifier.verifier_signing_key
                ):
                    return False
                if gateway_receipt.get("record_hash") != record_receipt.get("record_hash"):
                    return False
                if gateway_receipt.get("anchor_hash") != boot_receipt.get("anchor_hash"):
                    return False
            else:
                return False

            if not self_verifier._verify_signature(execution_trace, "signature", self_verifier.verifier_signing_key):
                return False
            if not self_verifier._verify_signature(execution_ledger_receipt, "witness_signature", self_verifier.witness_signing_key):
                return False
            if execution_ledger_receipt.get("record_id") != record_receipt.get("record_id"):
                return False
            if execution_ledger_receipt.get("execution_trace_hash") != execution_trace.get("trace_hash"):
                return False
            return True

        # Ensure both unoptimized and optimized return False for the invalid tx
        self.assertFalse(unoptimized_verify(self.verifier, capsule, invalid_tx))
        self.assertFalse(self.verifier.verify_transaction(capsule, invalid_tx))

        # Benchmarks
        number = 500

        def run_unoptimized():
            unoptimized_verify(self.verifier, capsule, invalid_tx)

        def run_optimized():
            self.verifier.verify_transaction(capsule, invalid_tx)

        time_unoptimized = timeit.timeit(run_unoptimized, number=number)
        time_optimized = timeit.timeit(run_optimized, number=number)

        ratio = time_optimized / time_unoptimized
        print(f"\n[Sentient Lock] verify_transaction Optimization Ratio: {ratio:.4f} (Lower is better)")

        self.assertLess(ratio, 1.0, "Severe performance regression detected: Deferring signature checks did not improve speed.")


if __name__ == "__main__":
    unittest.main()
