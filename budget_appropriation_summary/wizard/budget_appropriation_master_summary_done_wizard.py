from odoo import fields, models


class BudgetAppropriationMasterSummaryDoneWizard(models.TransientModel):
    _name = "budget.appropriation.master.summary.done.wizard"
    _description = "Confirm Master Summary Done"

    master_summary_id = fields.Many2one(
        comodel_name="budget.appropriation.master.summary",
        string="สรุปภาพรวมสถาบัน",
        required=True,
        readonly=True,
    )
    appropriation_count = fields.Integer(
        string="จำนวนรายการจัดสรร",
        compute="_compute_appropriation_count",
    )

    def _compute_appropriation_count(self):
        for record in self:
            summary = record.master_summary_id
            record.appropriation_count = len(
                summary.revenue_appropriation_ids + summary.expense_appropriation_ids
            )

    def action_confirm(self):
        self.ensure_one()
        summary = self.master_summary_id
        appropriations = (
            summary.revenue_appropriation_ids + summary.expense_appropriation_ids
        )
        for appropriation in appropriations:
            if appropriation.state == "draft":
                appropriation.action_review()
            if appropriation.state == "review":
                appropriation.action_post()
        summary.write({"state": "done"})
        return {"type": "ir.actions.act_window_close"}
