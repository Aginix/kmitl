# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ReceiptType(models.Model):
    _name = "receipt.kmitl.type"
    _description = "Receipt Type"
    _order = "sequence, code"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    suspense_account_id = fields.Many2one(
        "account.account",
        string="Suspense Account",
        domain="[('deprecated', '=', False)]",
        help="GL sub-account credited when a receipt of this type is issued, "
             "before central finance reclassifies it to a real income account. "
             "Must be configured before this type can be used on a receipt.",
    )
    default_income_account_id = fields.Many2one(
        "account.account",
        string="Default Income Account",
        domain="[('deprecated', '=', False), ('account_type', '=', 'income')]",
        help="Suggested income account when central finance creates a "
             "Suspense Allocation for receipts of this type.",
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Receipt Type code must be unique."),
    ]
