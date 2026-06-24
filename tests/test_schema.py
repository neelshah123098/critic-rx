import unittest

from clearrx.schema import (
    normalize_prediction,
    parse_prediction_content,
    validate_prediction_row,
)


class SchemaTests(unittest.TestCase):
    def test_aligned_nulls(self):
        normalized = normalize_prediction(
            "formalrx_0001",
            {
                "verdict": "aligned",
                "error_category": "N/A",
                "error_segment": "N/A",
                "corrected_statement": "N/A",
            },
        )
        self.assertTrue(normalized.ok)
        self.assertEqual(normalized.row["error_category"], None)

    def test_misaligned_valid_category(self):
        normalized = normalize_prediction(
            "formalrx_0002",
            {
                "verdict": "misaligned",
                "error_category": "Operator Confusion",
                "error_segment": "+",
                "corrected_statement": "theorem t : True := by trivial",
            },
        )
        self.assertTrue(normalized.ok)

    def test_bad_category_is_reported(self):
        normalized = normalize_prediction(
            "formalrx_0003",
            {
                "verdict": "misaligned",
                "error_category": "Made Up Category",
                "error_segment": "x",
                "corrected_statement": "theorem t : True := by trivial",
            },
        )
        self.assertFalse(normalized.ok)
        self.assertIn("unknown SCI category", normalized.errors[0])

    def test_category_alias_is_normalized(self):
        normalized = normalize_prediction(
            "formalrx_0004",
            {
                "verdict": "misaligned",
                "error_category": "Integration/Differentiation Confusion",
                "error_segment": "deriv f",
                "corrected_statement": "theorem t : True := by trivial",
            },
        )
        self.assertTrue(normalized.ok)
        self.assertEqual(normalized.row["error_category"], "Integration/Diff. Confusion")

    def test_parse_prediction_content(self):
        parsed = parse_prediction_content(
            '{"verdict":"aligned","error_category":null,"error_segment":null,"corrected_statement":null}'
        )
        self.assertEqual(parsed["verdict"], "aligned")

    def test_validate_row_rejects_extra_key(self):
        errors = validate_prediction_row(
            {
                "idx": "formalrx_0001",
                "verdict": "aligned",
                "error_category": None,
                "error_segment": None,
                "corrected_statement": None,
                "raw": "not allowed",
            }
        )
        self.assertTrue(any("extra fields" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
