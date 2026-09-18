# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_cash_movement_line = fields.Boolean(
        copy=False,
        index=True,
        readonly=True,
        help="This line pays nobody — it is one leg of the inter-account cash "
        "route the voucher's money travels through on its way to the paying "
        "account. Its Dr/Cr mirror always nets to zero.",
    )
