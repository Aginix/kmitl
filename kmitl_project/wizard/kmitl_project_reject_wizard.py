from odoo import _, fields, models


class KmitlProjectRejectWizard(models.TransientModel):
    _name = "kmitl.project.reject.wizard"
    _description = "KMITL Project Rejection Wizard"

    project_id = fields.Many2one(
        "kmitl.project",
        string="Project",
        required=True,
        readonly=True,
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
        required=True,
    )

    def action_reject(self):
        self.ensure_one()
        self.project_id.write(
            {
                "approval_state": "rejected",
                "rejection_reason": self.rejection_reason,
                "approval_user_id": self.env.user.id,
                "approval_date": fields.Datetime.now(),
            }
        )
        self.project_id.message_post(
            body=_("Project rejected by %s. Reason: %s")
            % (self.env.user.name, self.rejection_reason),
            message_type="notification",
        )
        return {"type": "ir.actions.act_window_close"}
