# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.budget_revenue_comparison.models.formula import (
    ActualResolver,
    BudgetResolver,
    eval_formula,
    validate_formula,
)


@tagged("post_install", "-at_install")
class TestFormulaEngine(TransactionCase):
    """The two-namespace formula engine: LIKE-matching, credit-positive
    actuals, within-row arithmetic and validation -- exercised through the real
    ``safe_eval`` (not a stand-in)."""

    def setUp(self):
        super().setUp()
        self.budget = BudgetResolver(
            {
                "4101000000": 1000000.0,
                "4102000000": 500000.0,
                "4201000000": 250000.0,
            }
        )
        self.actual = ActualResolver(
            [
                {"code": "4101000001", "type": "income", "value": 1500000.0},
                {"code": "4102000001", "type": "income", "value": 400000.0},
                {"code": "4900000001", "type": "income_other", "value": 50000.0},
                # A debit (refund) booked to income -> credit-positive value < 0
                {"code": "4199000001", "type": "income", "value": -20000.0},
            ]
        )

    def _eval(self, formula):
        return eval_formula(formula, self.budget, self.actual)

    def test_budget_code_pattern(self):
        self.assertAlmostEqual(self._eval("B['41%']"), 1500000.0)
        self.assertAlmostEqual(self._eval("B['4%']"), 1750000.0)
        self.assertAlmostEqual(self._eval("B['4101000000']"), 1000000.0)

    def test_actual_by_type_and_code(self):
        # Alphabetic selector -> account_type; '%' widens to income_other.
        self.assertAlmostEqual(self._eval("A['income']"), 1880000.0)
        self.assertAlmostEqual(self._eval("A['income%']"), 1930000.0)
        # Numeric selector -> CoA code.
        self.assertAlmostEqual(self._eval("A['41%']"), 1880000.0)

    def test_within_row_arithmetic(self):
        self.assertAlmostEqual(
            self._eval("A['income'] - A['4199%']"), 1900000.0
        )
        self.assertAlmostEqual(self._eval("B['41%'] + B['42%']"), 1750000.0)

    def test_empty_formula_is_zero(self):
        self.assertEqual(self._eval(""), 0.0)
        self.assertEqual(self._eval(False), 0.0)

    def test_validation_accepts_good_formulas(self):
        self.assertIsNone(validate_formula("B['41%'] - A['4199%']"))
        self.assertIsNone(validate_formula("(B['4%'] + B['5%']) * 1.0"))
        self.assertIsNone(validate_formula(""))

    def test_validation_rejects_bad_formulas(self):
        # Syntax error, unknown name, builtin access, empty selector.
        self.assertIsNotNone(validate_formula("B['41%'] +"))
        self.assertIsNotNone(validate_formula("foo['x']"))
        self.assertIsNotNone(validate_formula("__import__('os')"))
        self.assertIsNotNone(validate_formula("A['']"))
        self.assertIsNotNone(validate_formula("B['']"))


@tagged("post_install", "-at_install")
class TestReportLine(TransactionCase):
    """The configurable indicator rows: save-time validation and the
    header-clears-formulas onchange."""

    def setUp(self):
        super().setUp()
        self.Line = self.env["budget.revenue.report.line"]

    def test_bad_formula_raises_on_save(self):
        with self.assertRaises(ValidationError):
            self.Line.create(
                {
                    "name": "broken",
                    "row_type": "line",
                    "budget_formula": "B['41%'] +",
                }
            )

    def test_good_formula_saves(self):
        line = self.Line.create(
            {
                "name": "tuition",
                "row_type": "line",
                "budget_formula": "B['41%']",
                "actual_formula": "A['income']",
            }
        )
        self.assertTrue(line.id)

    def test_header_row_skips_formula_validation(self):
        # A header keeps whatever is in the formula fields but is never
        # validated or evaluated; creating one with junk must not raise.
        line = self.Line.create(
            {"name": "section", "row_type": "header", "budget_formula": "junk +"}
        )
        self.assertTrue(line.id)

    def test_onchange_header_clears_formulas(self):
        line = self.Line.new(
            {
                "name": "x",
                "row_type": "line",
                "budget_formula": "B['41%']",
                "actual_formula": "A['income']",
            }
        )
        line.row_type = "header"
        line._onchange_row_type_clear_formulas()
        self.assertFalse(line.budget_formula)
        self.assertFalse(line.actual_formula)


@tagged("post_install", "-at_install")
class TestComparisonCompute(TransactionCase):
    """The shared compute's row shaping: header rows carry no figures, the
    percentage is a dash (None) against a zero budget, and rows come out in
    sequence order. With no fiscal year/date both sides aggregate to nothing,
    so every formula resolves to 0.0 -- enough to exercise the shaping without
    seeding ledger data."""

    def setUp(self):
        super().setUp()
        self.Report = self.env["budget.revenue.comparison.report"]
        Line = self.env["budget.revenue.report.line"]
        self.header = Line.create(
            {"name": "รายได้จากการดำเนินงาน", "row_type": "header", "sequence": 1}
        )
        self.line = Line.create(
            {
                "name": "ค่าธรรมเนียมการศึกษา",
                "row_type": "line",
                "sequence": 2,
                "budget_formula": "B['41%']",
                "actual_formula": "A['income']",
            }
        )

    def test_row_to_id(self):
        rows = {
            r["id"]: r
            for r in self.Report.get_comparison_data({})["rows"]
        }
        header = rows[self.header.id]
        line = rows[self.line.id]
        # Header carries no figures.
        self.assertIsNone(header["budget"])
        self.assertIsNone(header["actual"])
        self.assertIsNone(header["percentage"])
        # Line aggregates to zero (no FY/date), so percentage is a dash (None).
        self.assertEqual(line["budget"], 0.0)
        self.assertEqual(line["actual"], 0.0)
        self.assertIsNone(line["percentage"])

    def test_percentage_against_nonzero_budget(self):
        # _row computes Actual / Budget * 100 when budget is non-zero.
        row = self.Report._row(self.line, 1000000.0, 1500000.0)
        self.assertAlmostEqual(row["percentage"], 150.0)
        # ...and None when budget is zero.
        self.assertIsNone(self.Report._row(self.line, 0.0, 500000.0)["percentage"])
