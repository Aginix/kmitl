from odoo import fields, models


class KrisProjectExceptionConfirm(models.TransientModel):
    _name = "kris.project.exception.confirm"
    _description = "KRIS Project Exception Wizard"
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one("kris.project", "KRIS Project")

    def action_confirm(self):
        self.ensure_one()
        exceptions_blocking = self.exception_ids.filtered("is_blocking")
        if self.ignore and not exceptions_blocking:
            self.related_model_id.ignore_exception = True
            action_name = self.env.context.get(
                "kris_exception_action", "action_confirm"
            )
            getattr(self.related_model_id, action_name)()
        else:
            self.related_model_id.ignore_exception = False
        return super().action_confirm()
