from odoo import _, fields, models
from odoo.exceptions import UserError


class ConstructionProjectEndWizard(models.TransientModel):

    _name = "construction.project.end.wizard"
    _description = "End Construction Project Wizard"

    project_id = fields.Many2one(
        comodel_name="construction.project",
        string="Construction Project",
        required=True,
        readonly=True,
    )

    date_end = fields.Date(
        string="End Date",
        required=True,
        default=fields.Date.context_today,
    )

    def action_end(self):
        self.ensure_one()
        if self.project_id.state != "in_progress":
            raise UserError(_("Only in-progress projects can be ended."))
        self.project_id.write({
            "state": "ended",
            "date_end": self.date_end,
        })
        return {"type": "ir.actions.act_window_close"}
