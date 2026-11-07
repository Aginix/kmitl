from odoo import fields, models


class KmitlProjectRevisionReason(models.TransientModel):
    _name = "kmitl.project.revision.reason"
    _description = "เหตุผลการปรับแผนโครงการ"

    project_id = fields.Many2one("kmitl.project", required=True)
    mode = fields.Selection(
        [("confirm", "ยืนยัน"), ("return", "ตีกลับ")], required=True, default="confirm"
    )
    reason = fields.Text(string="เหตุผล", required=True)

    def action_apply(self):
        self.ensure_one()
        project = self.project_id.with_context(active_test=False)
        if self.mode == "return":
            project.action_revision_return(self.reason)
        else:
            project.action_revision_confirm(self.reason)
        return {"type": "ir.actions.act_window_close"}
