# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestReceiptRemittance(ReceiptKmitlCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dept_a_child = cls.env["account.analytic.account"].create(
            {
                "name": "Department A / Sub",
                "code": "01-1",
                "plan_id": cls.dept_plan.id,
                "parent_id": cls.dept_a.id,
            }
        )

    def test_pull_submit_done_flow(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        r2 = self._make_receipt()
        r2.action_confirm()

        remittance = self.env["kmitl.receipt.remittance"].create(
            {"department_analytic_id": self.dept_a.id}
        )
        remittance.action_pull_pending_receipts()
        self.assertEqual(set(remittance.receipt_ids.ids), {r1.id, r2.id})
        self.assertEqual(remittance.amount_total, 10000.0)

        remittance.action_submit()
        self.assertEqual(remittance.state, "submitted")
        self.assertTrue(remittance.name.startswith("RM/"))
        self.assertEqual(remittance.date, remittance.submitted_date.date())

        remittance.action_done()
        self.assertEqual(remittance.state, "done")
        self.assertEqual(r1.state, "posted")
        self.assertEqual(r2.state, "posted")
        self.assertTrue(r1.move_id)
        self.assertTrue(r2.move_id)
        self.assertNotEqual(r1.move_id, r2.move_id)

    def test_pull_gathers_subtree(self):
        r_parent = self._make_receipt(department=self.dept_a)
        r_parent.action_confirm()
        r_child = self._make_receipt(department=self.dept_a_child)
        r_child.action_confirm()
        r_other = self._make_receipt(department=self.dept_b)
        r_other.action_confirm()

        remittance = self.env["kmitl.receipt.remittance"].create(
            {"department_analytic_id": self.dept_a.id}
        )
        remittance.action_pull_pending_receipts()
        self.assertEqual(
            set(remittance.receipt_ids.ids), {r_parent.id, r_child.id}
        )

    def test_pull_excludes_already_remitted(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        rm1 = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        rm1.action_submit()

        r2 = self._make_receipt()
        r2.action_confirm()
        rm2 = self.env["kmitl.receipt.remittance"].create(
            {"department_analytic_id": self.dept_a.id}
        )
        rm2.action_pull_pending_receipts()
        self.assertEqual(rm2.receipt_ids.ids, [r2.id])

    def test_detach_returns_receipt_to_pool(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        r2 = self._make_receipt()
        r2.action_confirm()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id, r2.id])],
            }
        )
        remittance.action_submit()

        r1.action_detach()
        self.assertFalse(r1.remittance_id)
        self.assertEqual(remittance.state, "submitted")
        self.assertEqual(remittance.receipt_ids, r2)

        remittance.action_done()
        self.assertEqual(r1.state, "confirmed")
        self.assertEqual(r2.state, "posted")

    def test_cancel_releases_all_receipts(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        remittance.action_submit()
        remittance.action_cancel()
        self.assertEqual(remittance.state, "cancelled")
        self.assertFalse(r1.remittance_id)

    def test_done_cannot_be_cancelled(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        remittance.action_submit()
        remittance.action_done()
        with self.assertRaises(UserError):
            remittance.action_cancel()

    def test_submitted_cannot_reset_to_draft(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        remittance.action_submit()
        with self.assertRaises(UserError):
            remittance.action_draft()

    def test_detach_blocked_on_done_remittance(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        remittance.action_submit()
        remittance.action_done()
        with self.assertRaises(UserError):
            r1.action_detach()
        self.assertTrue(r1.remittance_id)

    def test_detach_blocked_on_draft_remittance(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        with self.assertRaises(UserError):
            r1.action_detach()

    def test_submitted_remittance_date_is_submission_date(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        remittance.action_submit()
        fy_be = str(r1._get_fiscal_year_be(remittance.date))
        self.assertTrue(remittance.name.startswith("RM/%s/" % fy_be))

    def test_submit_rejects_receipt_outside_subtree(self):
        r_other = self._make_receipt(department=self.dept_b)
        r_other.action_confirm()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r_other.id])],
            }
        )
        with self.assertRaises(ValidationError):
            remittance.action_submit()
