from odoo import _, api, fields, models
from odoo.exceptions import UserError

ALLOWED_TRANSITIONS = {
    "in_progress": ("suspended", "terminated", "conditional_close", "done"),
    "suspended": ("in_progress", "terminated", "conditional_close", "done"),
}


class KrisProjectStateWizard(models.TransientModel):
    _name = "kris.project.state.wizard"
    _description = "KRIS Project State Change Wizard"

    project_id = fields.Many2one(
        "kris.project",
        string="Project",
        required=True,
    )
    current_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("suspended", "Suspended"),
            ("terminated", "Terminated"),
            ("conditional_close", "Closed with Conditions"),
            ("done", "Done"),
            ("cancel", "Cancel"),
        ],
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")
        if active_id and active_model == "kris.project":
            project = self.env["kris.project"].browse(active_id)
            res.setdefault("project_id", project.id)
            res.setdefault("current_state", project.state)
        return res
    # Two separate selection fields — the view shows the one matching current_state.
    # This avoids per-option "invisible" attrs which Odoo Selection widgets don't support.
    new_state_from_in_progress = fields.Selection(
        selection=[
            ("suspended", "Suspended"),
            ("terminated", "Terminated"),
            ("conditional_close", "Closed with Conditions"),
            ("done", "Done"),
        ],
        string="New Status",
    )
    new_state_from_suspended = fields.Selection(
        selection=[
            ("in_progress", "Resume"),
            ("terminated", "Terminated"),
            ("conditional_close", "Closed with Conditions"),
            ("done", "Done"),
        ],
        string="New Status",
    )
    new_state = fields.Selection(
        selection=[
            ("in_progress", "In Progress"),
            ("suspended", "Suspended"),
            ("terminated", "Terminated"),
            ("conditional_close", "Conditional Close"),
            ("done", "Done"),
        ],
        compute="_compute_new_state",
        store=False,
    )
    note = fields.Text(string="Note")

    @api.depends(
        "current_state",
        "new_state_from_in_progress",
        "new_state_from_suspended",
    )
    def _compute_new_state(self):
        for rec in self:
            if rec.current_state == "in_progress":
                rec.new_state = rec.new_state_from_in_progress
            elif rec.current_state == "suspended":
                rec.new_state = rec.new_state_from_suspended
            else:
                rec.new_state = False

    def action_apply(self):
        self.ensure_one()
        target = self.new_state
        if not target:
            raise UserError(_("Please select a new status."))
        allowed = ALLOWED_TRANSITIONS.get(self.current_state, ())
        if target not in allowed:
            raise UserError(
                _("Cannot change status from %s to %s.")
                % (self.current_state, target)
            )
        note = (self.note or "").strip()
        if target != "done" and not note:
            raise UserError(_("Please provide a note for this status change."))

        if note:
            self.project_id._track_set_log_message(
                _("<b>Note:</b> %s") % note,
            )
        self.project_id.write({"state": target})
        return {"type": "ir.actions.act_window_close"}
