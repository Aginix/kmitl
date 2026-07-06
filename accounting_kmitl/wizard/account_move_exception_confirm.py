# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveExceptionConfirm(models.TransientModel):
    _name = "account.move.exception.confirm"
    _description = "KMITL Account Move exception wizard"
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one("account.move", "Journal Entry")

    def action_confirm(self):
        self.ensure_one()
        exceptions_blocking = self.exception_ids.filtered("is_blocking")
        if self.ignore and not exceptions_blocking:
            self.related_model_id.ignore_exception = True
            self.related_model_id.action_submit()
        else:
            self.related_model_id.ignore_exception = False
        return super().action_confirm()
