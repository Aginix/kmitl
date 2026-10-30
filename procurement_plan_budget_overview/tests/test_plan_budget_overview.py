from odoo.tests.common import tagged

from odoo.addons.procurement_plan_budget_transfer.tests.test_procurement_plan_budget_transfer import (  # noqa: E501
    PlanTransferCommon,
)


@tagged("post_install", "-at_install")
class TestPlanBudgetOverview(PlanTransferCommon):
    """บัญชีแผน figures and the Plan Budget Movements (ADR-0006)."""

    def test_movements_and_figures(self):
        self._appropriate(self.src, 5000)
        plan = self._make_plan(5000)
        transfer = self._fund_plan_transfer(plan, 5000)
        transfer.action_submit()
        plan.invalidate_recordset()
        # In flight: shown as pending, not yet received.
        self.assertEqual(plan.budget_pending_amount, 5000)
        self.assertEqual(plan.budget_amount, 0)
        if transfer.state == "to_verify":
            transfer.action_verify()
        transfer.action_approve()
        plan.invalidate_recordset()
        rows = plan.budget_movement_ids
        self.assertEqual(rows.mapped("kind"), ["transfer_in"])
        self.assertEqual(rows.status, "posted")
        self.assertEqual(rows.amount, 5000)
        self.assertEqual(plan.budget_movement_count, 1)
        self.assertEqual(plan.budget_consumed, 0)
        self.assertEqual(plan.budget_remaining, 5000)
        self.assertEqual(plan.budget_pending_amount, 0)

    def test_plan_user_reads_movements_without_budget_rights(self):
        self._appropriate(self.src, 5000)
        plan = self._make_plan(5000)
        transfer = self._fund_plan_transfer(plan, 5000)
        self._post(transfer)
        user = self.env["res.users"].create(
            {
                "name": "PPBO Plan User",
                "login": "ppbo_plan_user",
                "groups_id": [
                    (4, self.env.ref("procurement_plan.group_procurement_plan_user").id)
                ],
                "operating_unit_ids": [(6, 0, plan.operating_unit_id.ids)],
                "default_operating_unit_id": plan.operating_unit_id.id,
            }
        )
        rows = (
            self.env["procurement.plan.budget.move.line"]
            .with_user(user)
            .search([("plan_id", "=", plan.id)])
        )
        self.assertEqual(len(rows), 1)
