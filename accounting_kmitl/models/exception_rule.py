# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    account_move_ids = fields.Many2many(
        comodel_name="account.move",
        string="Journal Entries",
    )
    model = fields.Selection(
        selection_add=[
            ("account.move", "Journal Entry"),
        ],
        ondelete={"account.move": "cascade"},
    )
