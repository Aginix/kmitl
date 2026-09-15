# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_wht_counterpart_line = fields.Boolean(
        copy=True,
        readonly=True,
        help="This line is one withholding-tax line's own mirror on the "
        "payable — it exists so the credit that reduced the payable (the tax "
        "withheld) has its own debit against the payable, instead of leaving "
        "the payable's debit as a single lump sum that has to be read against "
        "the tax line to be understood. Copy=True and not False: unlike a "
        "workflow stamp, this says what the line *is*, so a duplicated voucher "
        "must keep it on its duplicated line or the new voucher's rebuild sees "
        "two lines it thinks are both counterparts and breaks.",
    )
