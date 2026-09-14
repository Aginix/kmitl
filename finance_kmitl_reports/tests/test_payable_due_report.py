# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

REPORT = "finance_kmitl_reports.payable.due.report"


@tagged("post_install", "-at_install")
class TestPayableDueReport(TransactionCase):
    """รายงานเจ้าหนี้ถึงกำหนดชำระ: which bills fall in the window, what is
    carried as owing, and what the overdue switch reaches back for.

    The due dates sit more than a year out so the window holds nothing but this
    test's own bills. The one test that deliberately reaches backwards asserts
    on its own bills by number rather than on a total, because "everything
    already overdue" is a question about the whole ledger.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Move = cls.env["account.move"]
        cls.Report = cls.env[REPORT]
        cls.company = cls.env.company

        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.payable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.purchase_journal = cls.env.ref("account_kmitl.journal_ap")
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
                {"name": "payable %s" % code, "plan_id": plan.id}
            )
        cls.faculty = Account.create(
            {"name": "payable faculty", "plan_id": cls.dim["departments"].plan_id.id}
        )
        cls.dim["departments"].parent_id = cls.faculty
        cls.distribution = {str(account.id): 100 for account in cls.dim.values()}

        cls.vendor_type = cls.env["res.partner.type"].create(
            {"name": "Report Vendor Type", "company_type": "company"}
        )
        cls.vendor_one = cls._make_vendor("Report Vendor One")
        cls.vendor_two = cls._make_vendor("Report Vendor Two")

        cls.base = fields.Date.context_today(cls.env.user) + timedelta(days=400)
        cls.window = {
            "company_id": cls.company.id,
            "date_from": fields.Date.to_string(cls.base),
            "date_to": fields.Date.to_string(cls.base + timedelta(days=10)),
        }

    @classmethod
    def _make_vendor(cls, name):
        return cls.env["res.partner"].create(
            {
                "name": name,
                "partner_type_id": cls.vendor_type.id,
                "property_account_payable_id": cls.payable_account.id,
            }
        )

    # ------------------------------------------------------------------
    def _bill(self, due_date, amount=1000.0, vendor=None, post=True, ref=False):
        vendor = vendor or self.vendor_one
        bill = self.Move.create(
            {
                "move_type": "in_invoice",
                "partner_id": vendor.id,
                "invoice_date": fields.Date.context_today(self.env.user),
                "invoice_date_due": due_date,
                "journal_id": self.purchase_journal.id,
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
                            "account_id": self.expense_account.id,
                            "analytic_distribution": self.distribution,
                        },
                    )
                ],
            }
        )
        # No payment term is set: the office keeps them on the vendor master,
        # and the due date is what this report is ordered by, so the fixture
        # states it outright rather than deriving it.
        if post:
            bill.action_post()
        return bill

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
    def test_only_what_falls_due_in_the_window(self):
        inside = self._bill(self.base + timedelta(days=2))
        after = self._bill(self.base + timedelta(days=40))
        before = self._bill(self.base - timedelta(days=40))

        names = self._names(self._data())

        self.assertIn(inside.name, names)
        self.assertNotIn(after.name, names)
        self.assertNotIn(before.name, names)

    def test_the_overdue_switch_reaches_back_past_date_from(self):
        early = self._bill(self.base - timedelta(days=40))
        inside = self._bill(self.base + timedelta(days=2))
        after = self._bill(self.base + timedelta(days=40))

        names = self._names(self._data(include_overdue=True))

        self.assertIn(early.name, names)
        self.assertIn(inside.name, names)
        # date_to still bounds it in the other direction: this is a schedule of
        # what has to be paid by a day, not the whole ledger.
        self.assertNotIn(after.name, names)

    def test_a_draft_bill_is_not_owed_yet(self):
        draft = self._bill(self.base + timedelta(days=2), post=False)

        self.assertNotIn(draft.name or "/", self._names(self._data()))

    def test_a_partly_paid_bill_is_carried_at_what_is_left(self):
        bill = self._bill(self.base + timedelta(days=2), amount=1000.0)
        refund = self.Move.create(
            {
                "move_type": "in_refund",
                "partner_id": self.vendor_one.id,
                "invoice_date": fields.Date.context_today(self.env.user),
                "journal_id": self.purchase_journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": 400.0,
                            "account_id": self.expense_account.id,
                            "analytic_distribution": self.distribution,
                        },
                    )
                ],
            }
        )
        refund.action_post()
        payable_lines = (bill.line_ids + refund.line_ids).filtered(
            lambda line: line.account_id.account_type == "liability_payable"
        )
        payable_lines.reconcile()

        self.assertEqual(bill.payment_state, "partial")

        rows = {row["name"]: row for row in self._all_rows(self._data())}
        row = rows[bill.name]
        self.assertEqual(row["amount_total"], 1000.0)
        self.assertEqual(row["amount_residual"], 600.0)
        # The total is what is still owed, not the face value of the bill.
        self.assertEqual(self._data()["grand_total"], 600.0)

    def test_a_day_is_a_group_and_a_second_level_splits_it(self):
        self._bill(self.base + timedelta(days=2), amount=1000.0)
        self._bill(self.base + timedelta(days=2), amount=250.0, vendor=self.vendor_two)

        flat = self._data()
        self.assertEqual(len(flat["groups"]), 1)
        self.assertEqual(flat["groups"][0]["total"], 1250.0)
        self.assertEqual(flat["grand_total"], 1250.0)

        split = self._data(group_by="invoice_date_due", group_by_2="partner_id")
        day = split["groups"][0]
        self.assertFalse(day["rows"])
        self.assertEqual(len(day["subgroups"]), 2)
        self.assertEqual(sum(sub["total"] for sub in day["subgroups"]), 1250.0)

    def test_days_overdue_is_blank_until_it_is_late(self):
        future = self._bill(self.base + timedelta(days=2))
        overdue_by = 40
        late = self._bill(
            fields.Date.context_today(self.env.user) - timedelta(days=overdue_by)
        )

        rows = {
            row["name"]: row for row in self._all_rows(self._data(include_overdue=True))
        }

        self.assertEqual(rows[future.name]["days_overdue"], "")
        self.assertEqual(rows[late.name]["days_overdue"], overdue_by)

    def test_naming_a_faculty_finds_its_departments_bills(self):
        bill = self._bill(self.base + timedelta(days=2))

        self.assertIn(
            bill.name, self._names(self._data(dims={"departments": [self.faculty.id]}))
        )

    def test_a_vendor_picker_narrows_the_report(self):
        mine = self._bill(self.base + timedelta(days=2), amount=1000.0)
        self._bill(self.base + timedelta(days=2), amount=250.0, vendor=self.vendor_two)

        result = self._data(partner_ids=[self.vendor_one.id])

        self.assertEqual(self._names(result), {mine.name})
        self.assertEqual(result["grand_total"], 1000.0)

    def test_the_axes_and_the_columns_are_offered_by_the_server(self):
        axes = {axis["value"] for axis in self.Report.get_group_axes()}
        self.assertIn("invoice_date_due", axes)
        columns = [column[0] for column in self.Report.get_columns()]
        self.assertEqual(columns[0], "invoice_date_due")
        self.assertIn("amount_residual", columns)
