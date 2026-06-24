import unittest

from clearrx.prompting import FormalRxRow, render_user_prompt


class PromptingTests(unittest.TestCase):
    def test_row_prompt_shape(self):
        row = FormalRxRow(
            idx="formalrx_0001",
            header="import Mathlib",
            informal_statement="Every positive real number is nonzero.",
            formal_statement="theorem t (x : Real) (hx : 0 < x) : x != 0 := by sorry",
        )
        template = (
            "Header/context:\n{header}\n"
            "Informal statement:\n{informal_statement}\n"
            "Candidate Lean formal_statement:\n{formal_statement}"
        )
        prompt = render_user_prompt(row, template)
        self.assertIn("Header/context:\nimport Mathlib", prompt)
        self.assertIn("Informal statement:\nEvery positive real number is nonzero.", prompt)
        self.assertIn("Candidate Lean formal_statement:\ntheorem t", prompt)


if __name__ == "__main__":
    unittest.main()

