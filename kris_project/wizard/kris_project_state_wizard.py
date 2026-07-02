from odoo import _, api, fields, models
from odoo.exceptions import UserError

ALLOWED_TRANSITIONS = {
    "in_progress": ("suspended", "terminated", "conditional_close", "done"),
    "suspended": ("in_progress", "terminated", "conditional_close", "done"),
}

STATE_LABELS = {
    "in_progress": "ดำเนินการต่อ",
    "suspended": "ชะลอโครงการ",
    "terminated": "ยุติโครงการ",
    "conditional_close": "ปิดโครงการแบบมีเงื่อนไข",
    "done": "เสร็จสิ้น",
}


class KrisProjectStateWizard(models.TransientModel):
    _name = "kris.project.state.wizard"
    _description = "KRIS Project State Change Wizard"

    project_id = fields.Many2one(
        "kris.project",
        string="Project",
        required=True,
        default=lambda self: self.env.context.get("active_id"),
    )
    current_state = fields.Selection(
        related="project_id.state",
        readonly=True,
    )
    # Two separate selection fields — the view shows the one matching current_state.
    # This avoids per-option "invisible" attrs which Odoo Selection widgets don't support.
    new_state_from_in_progress = fields.Selection(
        selection=[
            ("suspended", "ชะลอโครงการ"),
            ("terminated", "ยุติโครงการ"),
            ("conditional_close", "ปิดโครงการแบบมีเงื่อนไข"),
            ("done", "เสร็จสิ้น"),
        ],
        string="สถานะใหม่",
    )
    new_state_from_suspended = fields.Selection(
        selection=[
            ("in_progress", "ดำเนินการต่อ (Resume)"),
            ("terminated", "ยุติโครงการ"),
            ("conditional_close", "ปิดโครงการแบบมีเงื่อนไข"),
            ("done", "เสร็จสิ้น"),
        ],
        string="สถานะใหม่",
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
    note = fields.Text(string="หมายเหตุ")

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
            raise UserError(_("กรุณาเลือกสถานะใหม่"))
        allowed = ALLOWED_TRANSITIONS.get(self.current_state, ())
        if target not in allowed:
            raise UserError(
                _("Cannot change status from %s to %s.")
                % (self.current_state, target)
            )
        if target != "done" and not (self.note and self.note.strip()):
            raise UserError(_("กรุณาระบุหมายเหตุสำหรับการปรับสถานะนี้"))

        self.project_id.write({"state": target})
        if self.note and self.note.strip():
            self.project_id.message_post(
                body=_("<b>ปรับสถานะเป็น %s</b><br/>หมายเหตุ: %s")
                % (STATE_LABELS.get(target, target), self.note),
            )
        return {"type": "ir.actions.act_window_close"}
