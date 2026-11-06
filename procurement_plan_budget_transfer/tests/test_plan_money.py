from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .test_procurement_plan_budget_transfer import PlanTransferCommon


@tagged("post_install", "-at_install")
class TestPlanMoney(PlanTransferCommon):
    """Reserve what was received (ADR-0003) and จัดสรรงบประมาณ (งบลอย) (ADR-0006)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("budget.allow_negative", False)

    def _fund(self, plan, amount):
        self._appropriate(self.src, amount)
        transfer = self._fund_plan_transfer(plan, amount)
        self._post(transfer)
        plan.invalidate_recordset()

    def _allocation(self, plan, amount):
        wizard = self.env["procurement.plan.floating.allocation"].create(
            {"plan_id": plan.id, "amount": amount}
        )
        return wizard

    def test_underfunded_plan_cannot_reserve(self):
        plan = self._make_plan(5000)
        self._fund(plan, 3000)
        self.assertEqual(plan.state, "to_verify")
        self.assertTrue(plan.budget_short)
        with self.assertRaisesRegex(UserError, "ยังไม่ครบวงเงินตามแผน"):
            plan.action_verify()

    def test_overfunded_plan_reserves_what_it_received(self):
        plan = self._make_plan(5000)
        self._fund(plan, 6000)
        self.assertEqual(plan.state, "verified")
        commitment = plan.budget_commitment_ids.filtered(lambda c: c.state != "cancel")
        self.assertEqual(commitment.amount, 6000)

    def test_floating_allocation_funds_and_reserves(self):
        # Floating money waits at the plan's coordinate without its dimension.
        self._appropriate(self.proc_account, 8000)
        plan = self._make_plan(5000)
        wizard = self._allocation(plan, 9000)
        self.assertTrue(wizard.pool_found)
        self.assertEqual(wizard.floating_available, 8000)
        with self.assertRaisesRegex(UserError, "เกินเงินลอยคงเหลือ"):
            wizard.action_next()
        wizard.amount = 5000
        wizard.action_next()
        self.assertEqual(wizard.step, "review")
        wizard.action_confirm()
        self.assertEqual(wizard.step, "done")
        self.assertTrue(wizard.transfer_id.is_procurement_plan_floating_allocation)
        self.assertEqual(wizard.transfer_id.state, "posted")
        plan.invalidate_recordset()
        self.assertEqual(plan.budget_amount, 5000)
        # Funded to its Plan Amount → reserved at once by the transfer bridge.
        self.assertEqual(plan.state, "verified")

    def test_floating_allocation_needs_budget_user(self):
        plan_user = self.env["res.users"].create(
            {
                "name": "PPM Plan User",
                "login": "ppm_plan_user",
                "groups_id": [
                    (4, self.env.ref("procurement_plan.group_procurement_plan_user").id)
                ],
            }
        )
        plan = self._make_plan(5000)
        with self.assertRaisesRegex(UserError, "Budget User"):
            plan.with_user(plan_user).action_open_floating_allocation()
