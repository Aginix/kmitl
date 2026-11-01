# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # A disbursement request pays out expenses: only the expense accounts
    # (code 5xxxxxxxxx) can be picked.
    account_id = fields.Many2one(
        domain="[('company_id', '=', company_id), ('deprecated', '=', False), "
        "('code', '=like', '5%')]",
    )
