from odoo import api, fields, models


class TodoLog(models.Model):
    _inherit = "todo.log"

    responsible_role_id = fields.Many2one("res.users.role", string="Responsible Role")
    operating_unit_id = fields.Many2one("operating.unit", string="Operating Unit")

    @api.model
    def _todo_log_vals(self, activity):
        """Capture the role-in-unit routing the chatter message does not carry."""
        vals = super()._todo_log_vals(activity)
        vals.update(
            {
                "responsible_role_id": activity.responsible_role_id.id,
                "operating_unit_id": activity.operating_unit_id.id,
            }
        )
        return vals
