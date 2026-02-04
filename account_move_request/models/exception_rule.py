# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    move_request_ids = fields.Many2many(
        comodel_name="account.move.request",
        string="Account Move Requests",
    )
    model = fields.Selection(
        selection_add=[
            ("account.move.request", "Account Move Requests"),
            ("account.move.request.line", "Account Move Requests line"),
        ],
        ondelete={
            "account.move.request": "cascade",
            "account.move.request.line": "cascade",
        },
    )
