from odoo import api, fields, models

from .mail_activity import TODO_CATEGORIES


class KmitlTodoLog(models.Model):
    """History of completed Todos (ADR-0004).

    Core unlinks a ``mail.activity`` when it is marked done, so this table keeps
    a snapshot taken at completion — preserving the role-in-unit routing the
    chatter message does not carry — for a cross-record "Completed Todos" view.
    """

    _name = "kmitl.todo.log"
    _description = "Completed Todo (history)"
    _order = "completed_date desc"

    activity_type_id = fields.Many2one("mail.activity.type", string="Activity Type")
    todo_category = fields.Selection(TODO_CATEGORIES, string="Category", index=True)
    summary = fields.Char()
    res_model_id = fields.Many2one("ir.model", string="App")
    res_model = fields.Char(string="Source Model", index=True)
    res_id = fields.Many2oneReference(string="Source ID", model_field="res_model")
    res_name = fields.Char(string="Source")
    user_id = fields.Many2one("res.users", string="Was assigned to")
    responsible_role_id = fields.Many2one("res.users.role", string="Responsible Role")
    operating_unit_id = fields.Many2one("operating.unit", string="Operating Unit")
    date_deadline = fields.Date(string="Was due")
    completed_by = fields.Many2one("res.users", string="Completed by", index=True)
    completed_date = fields.Datetime(string="Completed on", index=True)

    @api.model
    def _log_completed(self, activities):
        """Snapshot completed Todos (called from ``_action_done`` before unlink)."""
        now = fields.Datetime.now()
        vals = [
            {
                "activity_type_id": a.activity_type_id.id,
                "todo_category": a.todo_category,
                "summary": a.summary
                or a.activity_type_id.display_name
                or a.res_name,
                "res_model_id": a.res_model_id.id,
                "res_model": a.res_model,
                "res_id": a.res_id,
                "res_name": a.res_name,
                "user_id": a.user_id.id,
                "responsible_role_id": a.responsible_role_id.id,
                "operating_unit_id": a.operating_unit_id.id,
                "date_deadline": a.date_deadline,
                "completed_by": self.env.uid,
                "completed_date": now,
            }
            for a in activities
        ]
        if vals:
            self.sudo().create(vals)

    def action_open_document(self):
        """Open the (still-existing) source record of a completed Todo."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "views": [(False, "form")],
            "target": "current",
        }
