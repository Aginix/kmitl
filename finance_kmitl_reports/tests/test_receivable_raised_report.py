# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

REPORT = "finance_kmitl_reports.receivable.raised.report"


@tagged("post_install", "-at_install")
class TestReceivableRaisedReport(TransactionCase):
    """รายงานการตั้งลูกหนี้: which invoices fall in the window, and that a
    row is kept whether or not the debt has since been collected.

    The invoice dates sit more than a year out so the window holds nothing
    but this test's own invoices.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Move = cls.env["account.move"]
        cls.Report = cls.env[REPORT]
        cls.company = cls.env.company

        cls.income_account = cls.env["account.account"].search(
            [("account_type", "=", "income"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.receivable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_receivable"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.sale_journal = cls.env.ref("account_kmitl.journal_ar")
        cls.product = cls.env["product.product"].create(
            {"name": "Report Service", "type": "service"}
        )

        Plan = cls.env["account.analytic.plan"]
        Account = cls.env["account.analytic.account"]
        cls.dim = {}
        for code in ("departments", "sources", "funds", "activities"):
            plan = Plan.search([("code", "=", code)], limit=1)
            if not plan:
                plan = Plan.create({"name": code.title(), "code": code})
            cls.dim[code] = Account.create(
                {"name": "raised %s" % code, "plan_id": plan.id}
            )
        cls.faculty = Account.create(
            {"name": "raised faculty", "plan_id": cls.dim["departments"].plan_id.id}
        )
        cls.dim["departments"].parent_id = cls.faculty
        cls.distribution = {str(account.id): 100 for account in cls.dim.values()}

        cls.customer_type = cls.env["res.partner.type"].create(
            {"name": "Report Customer Type", "company_type": "company"}
        )
        cls.customer_one = cls._make_customer("Report Customer One")
        cls.customer_two = cls._make_customer("Report Customer Two")

        cls.base = fields.Date.context_today(cls.env.user) + timedelta(days=400)
        cls.window = {
            "company_id": cls.company.id,
            "date_from": fields.Date.to_string(cls.base),
            "date_to": fields.Date.to_string(cls.base + timedelta(days=10)),
        }

    @classmethod
    def _make_customer(cls, name):
        return cls.env["res.partner"].create(
            {
                "name": name,
                "partner_type_id": cls.customer_type.id,
                "property_account_receivable_id": cls.receivable_account.id,
            }
        )

    # ------------------------------------------------------------------
    def _invoice(
        self, invoice_date, amount=1000.0, customer=None, post=True, ref=False
    ):
        customer = customer or self.customer_one
        move = self.Move.create(
            {
                "move_type": "out_invoice",
                "partner_id": customer.id,
                "invoice_date": invoice_date,
                "invoice_date_due": invoice_date,
                "journal_id": self.sale_journal.id,
                "ref": ref or "",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": self.income_account.id,
                            "analytic_distribution": self.distribution,
                        },
                    )
                ],
            }
        )
        if post:
            move.action_post()
        return move

    def _data(self, **overrides):
        options = dict(self.window)
        options.update(overrides)
        return self.Report.get_report_data(options)

    def _all_rows(self, result):
        rows = []
        for group in result["groups"]:
            rows += group["rows"]
            for subgroup in group["subgroups"]:
                rows += subgroup["rows"]
        return rows

    def _names(self, result):
        return {row["name"] for row in self._all_rows(result)}

    # ------------------------------------------------------------------
    def test_only_what_is_invoiced_in_the_window(self):
        inside = self._invoice(self.base + timedelta(days=2))
        before = self._invoice(self.base - timedelta(days=40))
        after = self._invoice(self.base + timedelta(days=40))

        names = self._names(self._data())

        self.assertIn(inside.name, names)
        self.assertNotIn(before.name, names)
        self.assertNotIn(after.name, names)

    def test_a_draft_invoice_is_not_raised_yet(self):
        draft = self._invoice(self.base + timedelta(days=2), post=False)
        self.assertNotIn(draft.name or "/", self._names(self._data()))

    def test_a_paid_invoice_still_keeps_its_row(self):
        """A register of debt raised, so a row must not disappear once the
        debt is collected — what became of it is the due report's question,
        not this one's."""
        invoice = self._invoice(self.base + timedelta(days=2), amount=1000.0)
        refund = self.Move.create(
            {
                "move_type": "out_refund",
                "partner_id": self.customer_one.id,
                "invoice_date": fields.Date.context_today(self.env.user),
                "journal_id": self.sale_journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": 1000.0,
                            "account_id": self.income_account.id,
                            "analytic_distribution": self.distribution,
                        },
                    )
                ],
            }
        )
        refund.action_post()
        receivable_lines = (invoice.line_ids + refund.line_ids).filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        receivable_lines.reconcile()
        self.assertEqual(invoice.payment_state, "paid")

        rows = {row["name"]: row for row in self._all_rows(self._data())}
        self.assertIn(invoice.name, rows)
        self.assertEqual(rows[invoice.name]["amount_total"], 1000.0)
        self.assertEqual(rows[invoice.name]["amount_residual"], 0.0)

    def test_the_total_is_the_face_value_not_the_balance(self):
        """Unlike the due report, which totals amount_residual, this report
        answers "how much debt was raised" — the full face value, even for
        an invoice this test has already reconciled away in full."""
        invoice = self._invoice(self.base + timedelta(days=2), amount=1000.0)
        refund = self.Move.create(
            {
                "move_type": "out_refund",
                "partner_id": self.customer_one.id,
                "invoice_date": fields.Date.context_today(self.env.user),
                "journal_id": self.sale_journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": 1000.0,
                            "account_id": self.income_account.id,
                            "analytic_distribution": self.distribution,
                        },
                    )
                ],
            }
        )
        refund.action_post()
        (invoice.line_ids + refund.line_ids).filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        ).reconcile()

        self.assertEqual(self._data()["grand_total"], 1000.0)

    def test_a_day_is_a_group_and_a_second_level_splits_it(self):
        self._invoice(self.base + timedelta(days=2), amount=1000.0)
        self._invoice(
            self.base + timedelta(days=2), amount=250.0, customer=self.customer_two
        )

        flat = self._data()
        self.assertEqual(len(flat["groups"]), 1)
        self.assertEqual(flat["groups"][0]["total"], 1250.0)
        self.assertEqual(flat["grand_total"], 1250.0)

        split = self._data(group_by="invoice_date", group_by_2="partner_id")
        day = split["groups"][0]
        self.assertFalse(day["rows"])
        self.assertEqual(len(day["subgroups"]), 2)
        self.assertEqual(sum(sub["total"] for sub in day["subgroups"]), 1250.0)

    def test_naming_a_faculty_finds_its_departments_invoices(self):
        invoice = self._invoice(self.base + timedelta(days=2))
        self.assertIn(
            invoice.name,
            self._names(self._data(dims={"departments": [self.faculty.id]})),
        )

    def test_a_customer_picker_narrows_the_report(self):
        mine = self._invoice(self.base + timedelta(days=2), amount=1000.0)
        self._invoice(
            self.base + timedelta(days=2), amount=250.0, customer=self.customer_two
        )

        result = self._data(partner_ids=[self.customer_one.id])

        self.assertEqual(self._names(result), {mine.name})
        self.assertEqual(result["grand_total"], 1000.0)

    def test_the_axes_and_the_columns_are_offered_by_the_server(self):
        axes = {axis["value"] for axis in self.Report.get_group_axes()}
        self.assertIn("invoice_date", axes)
        columns = [column[0] for column in self.Report.get_columns()]
        self.assertEqual(columns[0], "invoice_date")
        self.assertIn("amount_residual", columns)
