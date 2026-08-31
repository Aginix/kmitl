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

    def test_full_flow(self):
        r1 = self._make_receipt()
        r1.action_to_submit()
        r2 = self._make_receipt()
        r2.action_to_submit()

        remittance = self.env["kmitl.receipt.remittance"].create(
            {"department_analytic_id": self.dept_a.id}
        )
        remittance.action_pull_pending_receipts()
        self.assertEqual(set(remittance.receipt_ids.ids), {r1.id, r2.id})

        remittance.action_submit()
        self.assertEqual(remittance.state, "submitted")
        self.assertEqual(r1.state, "submitted")
        self.assertEqual(r2.state, "submitted")

        remittance.action_approve()
        self.assertEqual(remittance.state, "approved")
        self.assertEqual(r1.state, "approved")
        self.assertEqual(r2.state, "approved")

        remittance.action_post()
        self.assertEqual(remittance.state, "posted")
        self.assertEqual(r1.state, "done")
        self.assertEqual(r2.state, "done")
        self.assertTrue(r1.move_id)
        self.assertTrue(r2.move_id)
        self.assertNotEqual(r1.move_id, r2.move_id)

    def test_pull_gathers_subtree(self):
        r_parent = self._make_receipt(department=self.dept_a)
        r_parent.action_to_submit()
        r_child = self._make_receipt(department=self.dept_a_child)
        r_child.action_to_submit()
        r_other = self._make_receipt(department=self.dept_b)
        r_other.action_to_submit()

        remittance = self.env["kmitl.receipt.remittance"].create(
            {"department_analytic_id": self.dept_a.id}
        )
        remittance.action_pull_pending_receipts()
        self.assertEqual(
            set(remittance.receipt_ids.ids), {r_parent.id, r_child.id}
        )

    def test_removing_receipt_returns_it_to_pool(self):
        r1 = self._make_receipt()
        r1.action_to_submit()
        r2 = self._make_receipt()
        r2.action_to_submit()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id, r2.id])],
            }
        )
        remittance.action_submit()

        remittance.write({"receipt_ids": [(3, r1.id)]})
        self.assertFalse(r1.remittance_id)
        self.assertEqual(r1.state, "to_submit")
        self.assertEqual(remittance.state, "submitted")

    def test_cancel_releases_receipts(self):
        r1 = self._make_receipt()
        r1.action_to_submit()
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
        self.assertEqual(r1.state, "to_submit")

    def test_posted_cannot_be_cancelled(self):
        r1 = self._make_receipt()
        r1.action_to_submit()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        remittance.action_submit()
        remittance.action_approve()
        remittance.action_post()
        with self.assertRaises(UserError):
            remittance.action_cancel()

    def test_reset_to_draft_from_submitted(self):
        r1 = self._make_receipt()
        r1.action_to_submit()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        remittance.action_submit()
        remittance.action_draft()
        self.assertEqual(remittance.state, "draft")
        self.assertEqual(r1.state, "to_submit")

    def test_submit_rejects_receipt_outside_subtree(self):
        r_other = self._make_receipt(department=self.dept_b)
        r_other.action_to_submit()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r_other.id])],
            }
        )
        with self.assertRaises(ValidationError):
            remittance.action_submit()
