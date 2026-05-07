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


if __name__ == "__main__":
    unittest.main()
