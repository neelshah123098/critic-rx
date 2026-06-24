import unittest

from clearrx.premodel_evidence import compose_evidence
from clearrx.taxonomy import SCI_28_CATEGORIES


class PremodelEvidenceTests(unittest.TestCase):
    def test_evidence_is_neutral_and_row_local(self):
        bundle = compose_evidence(
            {
                "idx": "toy_evidence",
                "header": "variable (f : Real -> Real)",
                "informal_statement": "For every positive real number x, f x is nonnegative.",
                "formal_statement": "theorem example (x : Real) : 0 <= f x := by sorry",
            }
        )
        self.assertEqual(bundle.idx, "toy_evidence")
        self.assertIn("informal_intent_cues", bundle.evidence)
        self.assertIn("lean_statement_cues", bundle.evidence)
        self.assertIn("semantic_checkpoints", bundle.evidence)
        self.assertNotIn("verdict_guess", bundle.system_prompt_block)
        self.assertIn("non-authoritative", bundle.system_prompt_block)
        self.assertIn("original row", bundle.system_prompt_block)

    def test_final_prompt_lists_all_categories_and_dynamic_hints(self):
        bundle = compose_evidence(
            {
                "idx": "toy_final",
                "header": "",
                "informal_statement": "For every function f, f * g is zero iff f is zero.",
                "formal_statement": (
                    "theorem example {f g : Nat -> Nat} : "
                    "f + g = 0 ↔ f = 0 := by sorry"
                ),
            }
        )
        self.assertIn("SCI-28 Valid Category Checklist", bundle.system_prompt_block)
        for category in SCI_28_CATEGORIES:
            self.assertIn(category, bundle.system_prompt_block)
        self.assertIn("Likely SCI Categories To Inspect", bundle.system_prompt_block)
        self.assertIn("Operator Confusion", bundle.system_prompt_block)
        self.assertIn("taxonomy_focus", bundle.evidence)
        self.assertNotIn("verdict_guess", bundle.system_prompt_block)


if __name__ == "__main__":
    unittest.main()
