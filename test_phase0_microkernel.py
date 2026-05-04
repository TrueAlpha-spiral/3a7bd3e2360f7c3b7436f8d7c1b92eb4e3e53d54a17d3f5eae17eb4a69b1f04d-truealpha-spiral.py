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


from unittest.mock import patch

class TestGuardAcceptsTokenAdversarial(unittest.TestCase):
    def setUp(self):
        self.signing_key = "test-secret"

        # Valid baseline token shape (before signature)
        self.valid_unsigned = {
            "status": "ALLOW_TOKEN_ISSUED",
            "proposal_id": "p1",
            "proposal_digest": "digest",
            "nonce": "n1",
            "counter": 1,
            "expires_in_seconds": 30,
            "one_shot": True,
            "token_hash": "hash"
        }

    def _sign(self, token_dict):
        from tas_phase0_microkernel import sign_payload
        return sign_payload(token_dict, self.signing_key)

    @patch("tas_phase0_microkernel.sign_payload")
    def test_replayed_counter_rejected_before_crypto(self, mock_sign):
        """1. Replayed counter is rejected before signature validation."""
        token = dict(self.valid_unsigned)
        token["signature"] = self._sign(token)
        used_counters = {1}

        mock_sign.reset_mock() # Reset mock after setup call to sign_payload
        result = guard_accepts_token(token, self.signing_key, used_counters)

        self.assertFalse(result)
        mock_sign.assert_not_called()

    @patch("tas_phase0_microkernel.sign_payload")
    def test_missing_one_shot_rejected_before_crypto(self, mock_sign):
        """2. Missing or false one_shot is rejected before signature validation."""
        token = dict(self.valid_unsigned)
        token["one_shot"] = False
        token["signature"] = self._sign(token)
        used_counters = set()

        mock_sign.reset_mock() # Reset mock after setup call to sign_payload
        result = guard_accepts_token(token, self.signing_key, used_counters)

        self.assertFalse(result)
        mock_sign.assert_not_called()

    @patch("tas_phase0_microkernel.sign_payload")
    def test_null_token_rejected_before_crypto(self, mock_sign):
        """3. Null/empty token is rejected before signature validation."""
        used_counters = set()

        result1 = guard_accepts_token(None, self.signing_key, used_counters)
        result2 = guard_accepts_token({}, self.signing_key, used_counters)

        self.assertFalse(result1)
        self.assertFalse(result2)
        mock_sign.assert_not_called()

    @patch("tas_phase0_microkernel.sign_payload")
    def test_unsigned_malformed_reaches_crypto(self, mock_sign):
        """4. Valid-looking but unsigned malformed token still reaches signature validation only after passing cheap preconditions."""
        # Setup mock to fail signature validation
        mock_sign.return_value = "different_signature"

        token = dict(self.valid_unsigned)
        token["signature"] = "fake_signature"
        used_counters = set()

        result = guard_accepts_token(token, self.signing_key, used_counters)

        self.assertFalse(result)
        mock_sign.assert_called_once()

    def test_used_counters_not_mutated_on_rejection(self):
        """5. used_counters is not mutated on any rejected token."""
        # Fail on one_shot
        token = dict(self.valid_unsigned)
        token["one_shot"] = False
        token["signature"] = self._sign(token)
        used_counters = {2}
        result = guard_accepts_token(token, self.signing_key, used_counters)
        self.assertFalse(result)
        self.assertEqual(used_counters, {2})

        # Fail on signature
        token = dict(self.valid_unsigned)
        token["signature"] = "fake"
        used_counters = {2}
        result = guard_accepts_token(token, self.signing_key, used_counters)
        self.assertFalse(result)
        self.assertEqual(used_counters, {2})

    def test_used_counters_mutated_on_success(self):
        """6. used_counters is mutated only after full signature validation succeeds."""
        token = dict(self.valid_unsigned)
        token["signature"] = self._sign(token)
        used_counters = {2}

        result = guard_accepts_token(token, self.signing_key, used_counters)

        self.assertTrue(result)
        self.assertEqual(used_counters, {1, 2})


if __name__ == "__main__":
    unittest.main()
