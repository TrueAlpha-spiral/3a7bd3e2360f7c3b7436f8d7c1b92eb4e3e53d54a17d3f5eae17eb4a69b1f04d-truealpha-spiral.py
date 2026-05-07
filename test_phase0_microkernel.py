import unittest

from tas_phase0_microkernel import (
    boot_microkernel,
    default_manifest,
    Phase0Manifest,
    ActionProposal,
    VerificationPolicy,
    verify_action,
    guard_accepts_token,
    BOOT_STATUS,
    REFUSAL_STATUS,
    ALLOW_STATUS,
    DENY_STATUS,
)


class TestPhase0MicroKernel(unittest.TestCase):
    def test_boot_success(self):
        receipt = boot_microkernel(default_manifest())
        self.assertEqual(receipt["status"], BOOT_STATUS)
        self.assertIn("anchor_hash", receipt)

    def test_refusal_on_low_coherence(self):
        bad = Phase0Manifest(
            phase="PHASE_0_MICRO_KERNEL_BOOT",
            steward="Russell",
            invariant="No attestation -> no execution",
            coherence=0.5,
        )
        receipt = boot_microkernel(bad)
        self.assertEqual(receipt["status"], REFUSAL_STATUS)

    def test_refusal_on_missing_invariant(self):
        bad = Phase0Manifest(
            phase="PHASE_0_MICRO_KERNEL_BOOT",
            steward="Russell",
            invariant="",
            coherence=1.0,
        )
        receipt = boot_microkernel(bad)
        self.assertEqual(receipt["status"], REFUSAL_STATUS)


class TestSplitTrustEnforcement(unittest.TestCase):
    def setUp(self):
        self.signing_key = "test-secret"
        self.policy = VerificationPolicy(
            allowed_actions=("OPEN_RELAY",),
            expected_attestation_digest="attested",
            expected_policy_hash="policy123",
        )

    def test_allowed_action_emits_token(self):
        proposal = ActionProposal(
            proposal_id="p1",
            action="OPEN_RELAY",
            nonce="n1",
            counter=1,
            attestation_digest="attested",
            policy_hash="policy123",
            previous_receipt_hash="0",
            snapshot_id="snap1",
        )
        receipt = verify_action(proposal, self.policy, self.signing_key)
        self.assertEqual(receipt["status"], ALLOW_STATUS)
        self.assertIsNotNone(receipt["actuation_token"])

    def test_denied_action_emits_signed_refusal(self):
        proposal = ActionProposal(
            proposal_id="p2",
            action="DELETE_ALL",
            nonce="n2",
            counter=1,
            attestation_digest="attested",
            policy_hash="policy123",
            previous_receipt_hash="0",
            snapshot_id="snap1",
        )
        receipt = verify_action(proposal, self.policy, self.signing_key)
        self.assertEqual(receipt["status"], DENY_STATUS)
        self.assertIsNone(receipt["actuation_token"])
        self.assertIn("signature", receipt)

    def test_guard_rejects_replay(self):
        proposal = ActionProposal(
            proposal_id="p3",
            action="OPEN_RELAY",
            nonce="n3",
            counter=1,
            attestation_digest="attested",
            policy_hash="policy123",
            previous_receipt_hash="0",
            snapshot_id="snap1",
        )
        receipt = verify_action(proposal, self.policy, self.signing_key)
        token = receipt["actuation_token"]

        used = set()
        self.assertTrue(guard_accepts_token(token, self.signing_key, used))
        self.assertFalse(guard_accepts_token(token, self.signing_key, used))


if __name__ == "__main__":
    unittest.main()
