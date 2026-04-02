from odoo import fields, models


class BudgetAppropriationF5PrintWizard(models.TransientModel):
    _name = "budget.appropriation.f5.print.wizard"
    _description = "F5 Print Options"

    show_note = fields.Boolean(string="แสดงหมายเหตุ", default=True)
    show_itemized = fields.Boolean(string="แสดงแจกแจงรหัสงบประมาณ", default=False)

    def action_print(self):
        self.ensure_one()
        active_ids = self.env.context.get("active_ids", [])
        appropriations = self.env["budget.appropriation"].browse(active_ids)
        return (
            self.env.ref(
                "budget_appropriation.action_report_budget_appropriation_f5"
            )
            .sudo()
            .report_action(
                appropriations,
                data={
                    "show_note": self.show_note,
                    "show_itemized": self.show_itemized,
                },
            )
        )
