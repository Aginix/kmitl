from odoo import api, fields, models

from .mail_activity import TODO_CATEGORIES


class TodoLog(models.Model):
    """History of completed Todos (ADR-0004).

    Core unlinks a ``mail.activity`` when it is marked done, so this table keeps
    a snapshot taken at completion — for a cross-record "Completed Todos" view.
    Layers extend the snapshot via ``_todo_log_vals`` (e.g. role-in-unit routing
    the chatter message does not carry).
    """

    _name = "todo.log"
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
    date_deadline = fields.Date(string="Was due")
    completed_by = fields.Many2one("res.users", string="Completed by", index=True)
    completed_date = fields.Datetime(string="Completed on", index=True)

    @api.model
    def _todo_log_vals(self, activity):
        """Snapshot values for one completed Todo. Layers override to add fields
        (e.g. responsible_role_id / operating_unit_id)."""
        return {
            "activity_type_id": activity.activity_type_id.id,
            "todo_category": activity.todo_category,
            "summary": activity.summary
            or activity.activity_type_id.display_name
            or activity.res_name,
            "res_model_id": activity.res_model_id.id,
            "res_model": activity.res_model,
            "res_id": activity.res_id,
            "res_name": activity.res_name,
            "user_id": activity.user_id.id,
            "date_deadline": activity.date_deadline,
            "completed_by": self.env.uid,
            "completed_date": fields.Datetime.now(),
        }

    @api.model
    def _log_completed(self, activities):
        """Snapshot completed Todos (called from ``_action_done`` before unlink)."""
        vals = [self._todo_log_vals(a) for a in activities]
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
