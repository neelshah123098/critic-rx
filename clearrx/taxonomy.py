"""SCI-28 taxonomy constants for FormalRx Track 1."""

SCI_28_CATEGORIES = (
    "Quantifier Strengthening",
    "Quantifier Weakening",
    "Logical Connective Misuse",
    "Object Type Error",
    "Function Confusion",
    "Operator Confusion",
    "Exponent/Power Error",
    "Coefficient/Constant Error",
    "Index/Subscript Error",
    "(Partial) Order Error",
    "Infinity Misinterpretation",
    "Extremum Concept Error",
    "Cardinality Error",
    "Integration/Diff. Confusion",
    "Geometric Error",
    "Positivity Constraint Error",
    "Bound Constraint Error",
    "Domain Constraint Error",
    "Variable Constraint Error",
    "Range Shift",
    "Range Error",
    "Missing Premise",
    "Redundant Premise",
    "Incorrect Premise",
    "Conclusion Error",
    "Auxiliary Construction Error",
    "Truncation Error",
    "Operator Precedence Error",
)

SCI_28_SET = frozenset(SCI_28_CATEGORIES)

CATEGORY_ALIASES = {
    "Integration/Differentiation Confusion": "Integration/Diff. Confusion",
}
