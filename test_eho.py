import unittest
from tas_pythonetics.eho_core import EthicalHamiltonian, EHO_PASSED, EHO_DENIED_DRIFT_TOO_HIGH, EHO_DENIED_MISSING_PROVENANCE, MAX_DRIFT_LIMIT

class TestEthicalHamiltonian(unittest.TestCase):
    def setUp(self):
        self.eho = EthicalHamiltonian("test_seed")
        self.valid_context = {
            "source": "human_auth",
            "scope": "local_test",
            "lineage": "hash_xyz",
            "authority": "steward",
            "admissibility": "verified"
        }

    def test_missing_provenance(self):
        invalid_context = self.valid_context.copy()
        del invalid_context["source"]

        status, drift = self.eho.evaluate_state(invalid_context, coherence=1.0, resonance=1.0)
        self.assertEqual(status, EHO_DENIED_MISSING_PROVENANCE)

    def test_valid_provenance_perfect_coherence(self):
        status, drift = self.eho.evaluate_state(self.valid_context, coherence=1.0, resonance=10.0, prior_drift=0.1)
        self.assertEqual(status, EHO_PASSED)
        self.assertEqual(drift, 0.1) # Drift shouldn't increase

    def test_drift_exceeds_limit(self):
        # 0.9 coherence, high resonance should spike drift
        status, drift = self.eho.evaluate_state(self.valid_context, coherence=0.5, resonance=2.0)
        self.assertEqual(status, EHO_DENIED_DRIFT_TOO_HIGH)
        self.assertGreater(drift, MAX_DRIFT_LIMIT)

if __name__ == '__main__':
    unittest.main()
