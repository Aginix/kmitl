# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.receipt_kmitl.tests.common import ReceiptKmitlCommon

REPORT = "finance_kmitl_reports.receipt.report"


@tagged("post_install", "-at_install")
class TestReceiptReport(ReceiptKmitlCommon):
    """รายงานการรับเงิน: what lands in it, which day it lands on, and how it
    folds up.

    Built on ``ReceiptKmitlCommon`` rather than a bare ``TransactionCase``: it
    already carries the analytic plans, the cash/bank accounts, the journals
    and the three payment methods a receipt needs. Every receipt here is
    dated more than a year out, so the window the report is asked for can
    hold nothing but this test's own records.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Report = cls.env[REPORT]

        # dept_a/dept_b are flat siblings in ReceiptKmitlCommon; give dept_a a
        # parent so "naming a faculty finds its departments' receipts" can be
        # asserted, the same fixture shape the payment/payable-due tests use.
        cls.faculty = cls.env["account.analytic.account"].create(
            {"name": "receipt report faculty", "plan_id": cls.dept_plan.id}
        )
        cls.dept_a.parent_id = cls.faculty.id

        cls.base = fields.Date.context_today(cls.env.user) + timedelta(days=400)
        cls.window = {
            "company_id": cls.company.id,
            "date_from": fields.Date.to_string(cls.base),
            "date_to": fields.Date.to_string(cls.base + timedelta(days=10)),
        }

    # ------------------------------------------------------------------
    def _receipt(self, date=None, department=None, method=None, amount=5000.0, **extra):
        extra_vals = {"date": date or self.base}
        extra_vals.update(extra)
        return self._make_receipt(
            department=department,
            method=method,
            lines=[(self.product_tuition, 1, amount)],
            extra_vals=extra_vals,
        )

    def _post_receipts(self, receipts):
        """Take receipts through the real submit -> approve -> post flow,
        rather than the internal ``_action_post()`` shortcut, whenever the
        test cares about the remittance itself (its date, its number)."""
        department = receipts[:1].department_analytic_id
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": department.id,
                "approver_id": self.env.user.id,
                "receipt_ids": [(6, 0, receipts.ids)],
            }
        )
        remittance.action_submit()
        remittance.action_approve()
        remittance.action_post()
        return remittance

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
        first = self._receipt(amount=1000.0)
        first._action_post()
        second = self._receipt(amount=250.0, method=self.pm_transfer)
        second._action_post()
        third = self._receipt(date=self.base + timedelta(days=1), amount=400.0)
        third._action_post()

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
        a = self._receipt(amount=1000.0)
        a._action_post()
        b = self._receipt(amount=250.0, method=self.pm_transfer)
        b._action_post()

        result = self._data(group_by="date", group_by_2="payment_method_id")

        self.assertEqual(len(result["groups"]), 1)
        day = result["groups"][0]
        self.assertEqual(day["total"], 1250.0)
        self.assertFalse(day["rows"])
        self.assertEqual(len(day["subgroups"]), 2)
        self.assertEqual(sum(sub["total"] for sub in day["subgroups"]), day["total"])
        self.assertEqual(result["grand_total"], 1250.0)

    def test_a_receipt_not_yet_done_is_not_in_it(self):
        draft = self._receipt()
        self.assertNotIn(draft.name, self._names(self._data()))

    def test_the_receipt_date_decides_the_report_not_the_remittance_date(self):
        """``kmitl.receipt._prepare_move_vals`` dates the journal entry — and
        this report — off ``receipt.date``. The remittance is only ever
        posted "today" in this test, which is never inside the far-future
        window, so a report that read the remittance's date would miss the
        receipt entirely."""
        receipt = self._receipt()
        remittance = self._post_receipts(receipt)

        self.assertNotEqual(remittance.date, receipt.date)
        rows = {row["name"]: row for row in self._all_rows(self._data())}
        self.assertEqual(rows[receipt.name]["date"], fields.Date.to_string(self.base))
        self.assertEqual(rows[receipt.name]["remittance"], remittance.name)

    def test_naming_a_faculty_finds_its_departments_receipts(self):
        mine = self._receipt(department=self.dept_a)
        mine._action_post()

        found = self._data(dims={"departments": [self.faculty.id]})
        self.assertIn(mine.name, self._names(found))

        elsewhere = self._data(dims={"departments": [self.dept_b.id]})
        self.assertNotIn(mine.name, self._names(elsewhere))

    def test_a_picker_narrows_the_report(self):
        by_cheque = self._receipt(method=self.pm_cheque, amount=300.0)
        by_cheque._action_post()
        by_cash = self._receipt(amount=700.0)
        by_cash._action_post()

        result = self._data(method_ids=[self.pm_cheque.id])

        self.assertEqual(self._names(result), {by_cheque.name})
        self.assertNotIn(by_cash.name, self._names(result))
        self.assertEqual(result["grand_total"], 300.0)

    def test_the_issuing_department_picker_is_exact_not_hierarchical(self):
        """Unlike the "Departments" dimension chip, ``department_ids`` is a
        plain ``in`` match on the stored column — picking the faculty must
        not also return its sub-department's receipts."""
        mine = self._receipt(department=self.dept_a)
        mine._action_post()

        result = self._data(department_ids=[self.faculty.id])
        self.assertNotIn(mine.name, self._names(result))

        exact = self._data(department_ids=[self.dept_a.id])
        self.assertIn(mine.name, self._names(exact))

    def test_payer_falls_back_to_the_partner_when_no_customer_name(self):
        receipt = self._receipt()
        receipt._action_post()

        rows = {row["name"]: row for row in self._all_rows(self._data())}
        self.assertEqual(rows[receipt.name]["payer"], self.walkin.display_name)

    def test_payer_prefers_the_customer_name_snapshot(self):
        receipt = self._receipt(customer_name="Somchai Jaidee")
        receipt._action_post()

        rows = {row["name"]: row for row in self._all_rows(self._data())}
        self.assertEqual(rows[receipt.name]["payer"], "Somchai Jaidee")

    def test_instrument_shows_the_cheque_number_and_date(self):
        receipt = self._receipt(method=self.pm_cheque)
        receipt._action_post()

        rows = {row["name"]: row for row in self._all_rows(self._data())}
        expected = "%s (%s)" % (
            receipt.cheque_number,
            fields.Date.to_string(receipt.cheque_date),
        )
        self.assertEqual(rows[receipt.name]["instrument"], expected)

    def test_instrument_shows_only_the_transfer_date(self):
        receipt = self._receipt(method=self.pm_transfer)
        receipt._action_post()

        rows = {row["name"]: row for row in self._all_rows(self._data())}
        self.assertEqual(
            rows[receipt.name]["instrument"],
            fields.Date.to_string(receipt.transfer_date),
        )

    def test_instrument_is_blank_on_cash_despite_a_stale_cheque_number(self):
        """``_onchange_payment_type`` only clears the cheque fields on the
        UI; a write that skips it can leave them behind on a receipt that is
        now cash — the column must read ``payment_type`` first, not fall
        back through whichever field happens to be set."""
        receipt = self._receipt()
        receipt._action_post()
        receipt.write({"cheque_number": "9990001", "cheque_date": self.base})

        rows = {row["name"]: row for row in self._all_rows(self._data())}
        self.assertEqual(rows[receipt.name]["instrument"], "")

    def test_the_axes_and_the_columns_are_offered_by_the_server(self):
        axes = {axis["value"] for axis in self.Report.get_group_axes()}
        self.assertIn("date", axes)
        columns = [column[0] for column in self.Report.get_columns()]
        self.assertEqual(columns[0], "date")
        self.assertEqual(columns[-1], "amount_total")
