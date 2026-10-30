from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .test_procurement_plan_budget_transfer import PlanTransferCommon


@tagged("post_install", "-at_install")
class TestPlanDeletion(PlanTransferCommon):
    """ลบแผน / ปิดแผน / โอนคืนงบลอย (procurement_plan ADR-0005)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan_user = cls.env["res.users"].create(
            {
                "name": "PPD Plan User",
                "login": "ppd_plan_user",
                "groups_id": [
                    (4, cls.env.ref("procurement_plan.group_procurement_plan_user").id)
                ],
            }
        )
        cls.env["ir.config_parameter"].sudo().set_param("budget.allow_negative", False)

    def _return_all(self, plan):
        wizard = self.env["procurement.plan.floating.return"].create(
            {"plan_id": plan.id}
        )
        wizard.amount = wizard.floating_available
        wizard.action_confirm()
        plan.invalidate_recordset()
        return wizard

    def _funded_plan(self, amount=5000, funded=None):
        self._appropriate(self.src, amount)
        plan = self._make_plan(amount)
        transfer = self._fund_plan_transfer(plan, funded or amount)
        self._post(transfer)
        plan.invalidate_recordset()
        return plan

    # --- delete ------------------------------------------------------------
    def test_unnumbered_draft_hard_deleted_by_plan_user(self):
        plan = self.env["procurement.plan"].create(
            {
                "description": "PPD unnumbered",
                "amount": 1,
                "unit": "ชุด",
                "total_price": 100,
                "account_fiscal_year_id": self.fy.id,
                "budget_account_id": self.proc_account.id,
            }
        )
        plan.with_user(self.plan_user).unlink()
        self.assertFalse(plan.exists())

    def test_numbered_plan_needs_manager_and_hard_deletes_analytic(self):
        plan = self._make_plan(5000)
        analytic = plan.analytic_account_id
        with self.assertRaisesRegex(UserError, "ผู้จัดการแผน"):
            plan.with_user(self.plan_user).unlink()
        plan.unlink()  # no Ledger Footprint → gone with its analytic
        self.assertFalse(plan.exists())
        self.assertFalse(analytic.exists())

    def test_held_money_blocks_delete_until_floating_return(self):
        plan = self._funded_plan(5000, funded=3000)  # to_verify, 3000 allocated
        self.assertEqual(plan.state, "to_verify")
        self.assertTrue(plan.has_held_money)
        with self.assertRaisesRegex(UserError, "มีงบประมาณค้างในมิติแผน"):
            plan.unlink()
        wizard = self._return_all(plan)
        self.assertEqual(wizard.floating_available, 3000)
        self.assertFalse(plan.has_held_money)
        self.assertEqual(plan.budget_amount, 0)
        plan.unlink()  # footprint, never spent → soft delete
        self.assertTrue(plan.exists())
        self.assertEqual(plan.state, "cancel")
        self.assertFalse(plan.active)
        self.assertFalse(plan.analytic_account_id.active)
        plan.action_reset_to_draft()  # revives both, same number
        self.assertEqual(plan.state, "draft")
        self.assertTrue(plan.active)
        self.assertTrue(plan.analytic_account_id.active)

    def test_floating_return_releases_reservation(self):
        plan = self._funded_plan(5000)  # fully funded → auto-reserved
        self.assertEqual(plan.state, "verified")
        commitment = plan.budget_commitment_ids.filtered(lambda c: c.state != "cancel")
        self.assertEqual(commitment.available_to_obligate, 5000)
        reasons = plan._get_held_money_reasons()
        self.assertEqual(len(reasons), 2, reasons)  # allocation + reservation
        self._return_all(plan)
        commitment.invalidate_recordset()
        self.assertEqual(commitment.available_to_obligate, 0)
        self.assertFalse(plan._get_held_money_reasons())
        plan.unlink()
        self.assertEqual(plan.state, "cancel")

    def test_floating_return_capped(self):
        plan = self._funded_plan(5000)
        wizard = self.env["procurement.plan.floating.return"].create(
            {"plan_id": plan.id, "amount": 6000}
        )
        with self.assertRaisesRegex(UserError, "เกินยอดที่โอนคืนได้"):
            wizard.action_confirm()

    def test_retarget_blocked_while_money_held(self):
        plan = self._funded_plan(5000, funded=3000)
        with self.assertRaisesRegex(UserError, "ไม่สามารถเปลี่ยนรหัสงบประมาณ"):
            plan.write({"budget_account_id": self.src.id})

    # --- close -------------------------------------------------------------
    def test_close_only_in_progress_and_returns_reservation(self):
        plan = self._funded_plan(5000)
        with self.assertRaisesRegex(UserError, "อยู่ในระหว่างดำเนินการ"):
            plan.action_done()
        plan.action_in_progress()
        with self.assertRaisesRegex(UserError, "ผู้จัดการแผน"):
            plan.with_user(self.plan_user).action_done()
        plan.action_done()
        self.assertEqual(plan.state, "done")
        commitment = plan.budget_commitment_ids.filtered(lambda c: c.state != "cancel")
        self.assertEqual(commitment.available_to_obligate, 0)
        # The money stays at the plan's dimension until a Floating Return.
        self.assertTrue(plan.has_held_money)
        with self.assertRaisesRegex(UserError, "ปิดแล้ว"):
            plan.unlink()

    def test_reset_needs_manager(self):
        plan = self._make_plan(5000)
        with self.assertRaisesRegex(UserError, "ผู้จัดการแผน"):
            plan.with_user(self.plan_user).action_reset_to_draft()

    # --- responsible -------------------------------------------------------
    def test_responsible_follows_plan(self):
        plan = self._make_plan(5000)
        plan.responsible_id = self.plan_user
        self.assertIn(self.plan_user.partner_id, plan.message_partner_ids)
