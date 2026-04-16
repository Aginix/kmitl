from odoo import fields, models


class CompilationF5PrintWizard(models.TransientModel):
    _name = "budget.appropriation.compilation.f5.print.wizard"
    _description = "Compilation F5 Print Options"

    show_note = fields.Boolean(string="แสดงหมายเหตุ", default=True)
    show_itemized = fields.Boolean(string="แสดงแจกแจงรหัสงบประมาณ", default=False)

    def action_print(self):
        self.ensure_one()
        active_id = self.env.context.get("active_id")
        compilation = self.env["budget.appropriation.compilation"].browse(active_id)
        return (
            self.env.ref(
                "budget_appropriation_summary.action_report_compilation_f5"
            )
            .sudo()
            .report_action(
                compilation,
                data={
                    "show_note": self.show_note,
                    "show_itemized": self.show_itemized,
                },
            )
        )

    def action_preview(self):
        self.ensure_one()
        active_id = self.env.context.get("active_id")
        params = []
        if not self.show_note:
            params.append("show_note=0")
        if self.show_itemized:
            params.append("show_itemized=1")
        url = f"/budget_appropriation_summary/compilation/{active_id}/f5/html"
        if params:
            url += "?" + "&".join(params)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }
