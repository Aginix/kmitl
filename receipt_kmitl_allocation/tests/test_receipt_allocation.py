# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from odoo.addons.receipt_kmitl.tests.common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestReceiptAllocation(ReceiptKmitlCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Account = cls.env["account.account"]
        cls.institute_account = Account.create(
            {
                "code": "410201",
                "name": "ค่าบำรุงสถาบัน",
                "account_type": "income",
                "company_id": cls.company.id,
            }
        )
        cls.faculty_account = Account.create(
            {
                "code": "410202",
                "name": "ค่าธรรมเนียมการศึกษา (คณะ)",
                "account_type": "income",
                "company_id": cls.company.id,
            }
        )
        cls.registrar_account = Account.create(
            {
                "code": "410203",
                "name": "ค่าบริการสำนักทะเบียน",
                "account_type": "income",
                "company_id": cls.company.id,
            }
        )
        cls.product_fee = cls.env["product.product"].create(
            {
                "name": "ค่าธรรมเนียมการศึกษา",
                "type": "service",
                "company_id": cls.company.id,
                "property_account_income_id": cls.income_tuition.id,
                "lst_price": 10000.0,
            }
        )

    def _set_buckets(self, product, buckets_vals):
        # All buckets for a product must be created together: the "at least
        # one percent bucket summing to 100" constraint is checked at the
        # end of each create/write, so adding rows one create() at a time
        # would fail on the very first (incomplete) row. Real usage saves
        # every row in one product-form write, which this batch create()
        # mirrors.
        vals_list = []
        for vals in buckets_vals:
            base = {
                "product_tmpl_id": product.product_tmpl_id.id,
                "name": "Bucket",
                "account_id": self.faculty_account.id,
                "method": "percent",
                "percentage": 100.0,
            }
            base.update(vals)
            vals_list.append(base)
        return self.env["receipt.allocation.line"].create(vals_list)

    def test_regression_product_without_buckets_move_unchanged(self):
        receipt = self._make_receipt(
            lines=[(self.product_tuition, 1, 5000.0), (self.product_card, 2, 100.0)]
        )
        receipt._action_post()
        lines = receipt.move_id.line_ids
        self.assertEqual(len(lines), 2 * len(receipt.line_ids) + 2)
        credit_lines = lines.filtered(lambda l: l.credit > 0 and l.account_id != self.cash_account)
        self.assertEqual(
            set(credit_lines.mapped("account_id")),
            {self.income_tuition, self.income_other},
        )

    def test_fixed_and_percent_split_with_dimension_overrides(self):
        self._set_buckets(
            self.product_fee,
            [
                {
                    "name": "ค่าบำรุงสถาบัน",
                    "account_id": self.institute_account.id,
                    "method": "fixed",
                    "percentage": 0.0,
                    "fixed_amount": 100.0,
                    "department_analytic_id": self.dept_b.id,
                },
                {
                    "name": "ค่าธรรมเนียมการศึกษา (คณะ)",
                    "account_id": self.faculty_account.id,
                    "method": "percent",
                    "percentage": 70.0,
                },
                {
                    "name": "ค่าบริการสำนักทะเบียน",
                    "account_id": self.registrar_account.id,
                    "method": "percent",
                    "percentage": 30.0,
                    "department_analytic_id": self.dept_b.id,
                },
            ],
        )

        receipt = self._make_receipt(
            department=self.dept_a,
            lines=[(self.product_fee, 1, 10000.0)],
        )
        receipt._action_post()
        lines = receipt.move_id.line_ids

        cash_debit = lines.filtered(lambda l: l.account_id == self.cash_account and l.debit)
        self.assertEqual(len(cash_debit), 1)
        self.assertEqual(cash_debit.debit, 10000.0)
        self.assertEqual(cash_debit.analytic_distribution, receipt.line_ids.analytic_distribution)

        institute_leg = lines.filtered(lambda l: l.account_id == self.institute_account)
        faculty_leg = lines.filtered(lambda l: l.account_id == self.faculty_account)
        registrar_leg = lines.filtered(lambda l: l.account_id == self.registrar_account)
        self.assertEqual(institute_leg.credit, 100.0)
        self.assertEqual(faculty_leg.credit, 6930.0)
        self.assertEqual(registrar_leg.credit, 2970.0)

        # Merged distribution: department entry swapped for the bucket's
        # pinned unit, every other dimension (e.g. Source) carried over
        # unchanged from the line/header.
        line_dist = receipt.line_ids.analytic_distribution
        expected_pinned = dict(line_dist)
        expected_pinned.pop(str(self.dept_a.id), None)
        expected_pinned[str(self.dept_b.id)] = 100
        self.assertEqual(institute_leg.analytic_distribution, expected_pinned)
        self.assertEqual(registrar_leg.analytic_distribution, expected_pinned)
        self.assertEqual(faculty_leg.analytic_distribution, line_dist)

        credit_total = institute_leg.credit + faculty_leg.credit + registrar_leg.credit
        self.assertEqual(credit_total, 10000.0)

    def test_rounding_residual_lands_on_last_percent_bucket(self):
        self._set_buckets(
            self.product_fee,
            [
                {"name": "A", "percentage": 33.33},
                {
                    "name": "B",
                    "account_id": self.institute_account.id,
                    "percentage": 33.33,
                },
                {
                    "name": "C",
                    "account_id": self.registrar_account.id,
                    "percentage": 33.34,
                },
            ],
        )
        receipt = self._make_receipt(lines=[(self.product_fee, 1, 10.0)])
        receipt._action_post()
        credit_lines = receipt.move_id.line_ids.filtered(
            lambda l: l.credit > 0 and l.account_id != self.cash_account
        )
        self.assertAlmostEqual(sum(credit_lines.mapped("credit")), 10.0, places=2)

    def test_fixed_exceeding_line_amount_raises(self):
        self._set_buckets(
            self.product_fee,
            [
                {
                    "name": "Too much fixed",
                    "method": "fixed",
                    "percentage": 0.0,
                    "fixed_amount": 15000.0,
                },
                {"name": "Remainder", "percentage": 100.0},
            ],
        )
        receipt = self._make_receipt(lines=[(self.product_fee, 1, 10000.0)])
        with self.assertRaises(UserError):
            receipt._action_post()

    def test_config_requires_at_least_one_percent_bucket(self):
        with self.assertRaises(ValidationError):
            self._set_buckets(
                self.product_fee,
                [
                    {
                        "name": "Only fixed",
                        "method": "fixed",
                        "percentage": 0.0,
                        "fixed_amount": 100.0,
                    },
                ],
            )

    def test_config_percent_buckets_must_sum_to_100(self):
        with self.assertRaises(ValidationError):
            self._set_buckets(self.product_fee, [{"name": "A", "percentage": 60.0}])
