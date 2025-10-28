# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    state = fields.Selection(
        selection_add=[("submitted", "Submitted")],
        ondelete={"submitted": "set default"},
    )
