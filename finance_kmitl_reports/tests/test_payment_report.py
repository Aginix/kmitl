# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

REPORT = "finance_kmitl_reports.payment.report"


@tagged("post_install", "-at_install")
class TestPaymentReport(TransactionCase):
    """รายงานการจ่ายเงิน: what lands in it, which day it lands on, and how it
    folds up.

    Every voucher here is dated more than a year out, so the window the report
    is asked for can hold nothing but this test's own records — the finance
    office's own demo data and anything else in the database sits in the past.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Payment = cls.env["account.payment"]
        cls.Export = cls.env["bank.payment.export"]
        cls.Report = cls.env[REPORT]

        cls.transfer_account = cls.env.ref(
            "account_kmitl.paying_account_1112120002_transfer"
        )
        cls.cheque_account = cls.env.ref(
            "account_kmitl.paying_account_1112220015_cheque"
        )
        cls.cash_account = cls.env.ref("account_kmitl.paying_account_1111000002_cash")
        cls.payment_type = cls.env.ref("finance_kmitl.payment_type_normal_outbound")
        cls.payable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", cls.env.company.id),
            ],
            limit=1,
        )

        # The four dimensions, with ส่วนงาน given a parent so "a faculty finds
        # its departments' vouchers" can be asserted.
        Plan = cls.env["account.analytic.plan"]
        Account = cls.env["account.analytic.account"]
        cls.dim = {}
        for code in ("departments", "sources", "funds", "activities"):
            plan = Plan.search([("code", "=", code)], limit=1)
            if not plan:
                plan = Plan.create({"name": code.title(), "code": code})
            cls.dim[code] = Account.create(
                {"name": "report %s" % code, "plan_id": plan.id}
            )
        cls.faculty = Account.create(
            {"name": "report faculty", "plan_id": cls.dim["departments"].plan_id.id}
        )
        cls.dim["departments"].parent_id = cls.faculty
        cls.distribution = {str(account.id): 100 for account in cls.dim.values()}
        cls.other_department = Account.create(
            {
                "name": "report other department",
                "plan_id": cls.dim["departments"].plan_id.id,
            }
        )

        cls.payee_one = cls._make_payee("Report Payee One")
        cls.payee_two = cls._make_payee("Report Payee Two")

        # A year and more out: nothing else in the database is paid then.
        cls.base = fields.Date.context_today(cls.env.user) + timedelta(days=400)
        cls.window = {
            "company_id": cls.env.company.id,
            "date_from": fields.Date.to_string(cls.base),
            "date_to": fields.Date.to_string(cls.base + timedelta(days=10)),
        }

    @classmethod
    def _make_payee(cls, name):
        partner = cls.env["res.partner"].create(
            {"name": name, "property_account_payable_id": cls.payable_account.id}
        )
        cls.env["res.partner.bank"].create(
            {
                "partner_id": partner.id,
                "acc_number": "ACC-%s" % name.replace(" ", "-"),
                "bank_id": cls.transfer_account.bank_id.id,
            }
        )
        return partner

    # ------------------------------------------------------------------
    def _payment(
        self, paying_account, payee=None, amount=1000.0, date=None, distribution=None
    ):
        payee = payee or self.payee_one
        payment = self.Payment.create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": payee.id,
                "partner_bank_id": payee.bank_ids[:1].id,
                "amount": amount,
                "date": date or self.base,
                "journal_id": paying_account.journal_id.id,
                "payment_method_line_id": paying_account.id,
                "kmitl_payment_type_id": self.payment_type.id,
                "analytic_distribution": distribution or self.distribution,
            }
        )
        payment.action_confirm_for_bank()
        return payment

    def _transfer(self, effective_date, **kwargs):
        payment = self._payment(self.transfer_account, **kwargs)
        export = self.Export.create(
            {
                "paying_account_id": self.transfer_account.id,
                "effective_date": effective_date,
                "export_line_ids": [(0, 0, {"payment_id": payment.id})],
            }
        )
        export.action_confirm()
        export.action_done()
        payment._mark_paid()
        return payment

    def _cheque(self, cheque_date, number="9990001", **kwargs):
        payment = self._payment(self.cheque_account, **kwargs)
        payment.action_create_cheques()
        payment.cheque_id.write({"cheque_number": number, "cheque_date": cheque_date})
        payment._mark_paid()
        return payment

    def _cash(self, **kwargs):
        payment = self._payment(self.cash_account, **kwargs)
        payment._mark_paid()
        return payment

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
    def test_a_day_is_a_group_and_the_totals_add_up(self):
        first = self._transfer(self.base, amount=1000.0)
        second = self._transfer(self.base, amount=250.0, payee=self.payee_two)
        third = self._cash(date=self.base + timedelta(days=1), amount=400.0)

        result = self._data()

        self.assertEqual(len(result["groups"]), 2)
        day_one, day_two = result["groups"]
        self.assertEqual(day_one["label"], fields.Date.to_string(self.base))
        self.assertEqual(day_one["total"], 1250.0)
        self.assertEqual(day_two["total"], 400.0)
        self.assertEqual(result["grand_total"], 1650.0)
        self.assertEqual(self._names(result), {first.name, second.name, third.name})
        # No second level asked for, so the rows hang straight off the day.
        self.assertFalse(day_one["subgroups"])
        self.assertEqual(len(day_one["rows"]), 2)

    def test_a_second_level_splits_the_day_without_changing_the_total(self):
        self._transfer(self.base, amount=1000.0)
        self._cheque(self.base, amount=250.0)

        result = self._data(group_by="paid_date", group_by_2="payment_method_id")

        self.assertEqual(len(result["groups"]), 1)
        day = result["groups"][0]
        self.assertEqual(day["total"], 1250.0)
        self.assertFalse(day["rows"])
        self.assertEqual(len(day["subgroups"]), 2)
        self.assertEqual(sum(sub["total"] for sub in day["subgroups"]), day["total"])
        self.assertEqual(result["grand_total"], 1250.0)

    def test_the_file_decides_the_month_not_the_voucher(self):
        """A voucher authorised before its file takes effect is October's
        payment, and September must not show it."""
        voucher_day = fields.Date.context_today(self.env.user)
        effective = self.base + timedelta(days=2)
        payment = self._transfer(effective, date=voucher_day)

        in_effect = self._data()
        self.assertIn(payment.name, self._names(in_effect))
        self.assertEqual(
            in_effect["groups"][0]["label"], fields.Date.to_string(effective)
        )

        when_authorised = self._data(
            date_from=fields.Date.to_string(voucher_day),
            date_to=fields.Date.to_string(voucher_day),
        )
        self.assertNotIn(payment.name, self._names(when_authorised))

    def test_a_voucher_that_is_not_paid_yet_is_not_in_it(self):
        """`done` on a file is not `paid` on a voucher — finance_kmitl
        ADR-0004."""
        unpaid = self._payment(self.cash_account)

        self.assertNotIn(unpaid.name, self._names(self._data()))

    def test_naming_a_faculty_finds_its_departments_vouchers(self):
        mine = self._cash(amount=100.0)

        found = self._data(dims={"departments": [self.faculty.id]})
        self.assertIn(mine.name, self._names(found))

        elsewhere = self._data(dims={"departments": [self.other_department.id]})
        self.assertNotIn(mine.name, self._names(elsewhere))

    def test_a_picker_narrows_the_report(self):
        by_cheque = self._cheque(self.base, amount=300.0)
        by_cash = self._cash(amount=700.0)

        result = self._data(paying_account_ids=[self.cheque_account.id])

        self.assertEqual(self._names(result), {by_cheque.name})
        self.assertNotIn(by_cash.name, self._names(result))
        self.assertEqual(result["grand_total"], 300.0)

    def test_the_reference_column_names_the_instrument(self):
        transfer = self._transfer(self.base)
        cheque = self._cheque(self.base, number="9990002")
        cash = self._cash()

        rows = {row["name"]: row for row in self._all_rows(self._data())}

        self.assertEqual(
            rows[transfer.name]["reference"], transfer.payment_export_id.name
        )
        self.assertEqual(rows[cheque.name]["reference"], "9990002")
        self.assertEqual(rows[cash.name]["reference"], "")

    def test_an_unknown_axis_falls_back_to_the_day(self):
        """The dropdown is built from ``get_group_axes``, but the RPC is public
        and a stale screen must not fold the report by nothing."""
        self._cash(amount=100.0)

        result = self._data(group_by="whatever", group_by_2="whatever")

        self.assertEqual(result["groups"][0]["label"], fields.Date.to_string(self.base))
        self.assertFalse(result["groups"][0]["subgroups"])

    def test_the_axes_and_the_columns_are_offered_by_the_server(self):
        axes = {axis["value"] for axis in self.Report.get_group_axes()}
        self.assertIn("paid_date", axes)
        columns = [column[0] for column in self.Report.get_columns()]
        self.assertEqual(columns[0], "paid_date")
        self.assertEqual(columns[-1], "amount")
