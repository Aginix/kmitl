# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ReceiptPaymentMethod(models.Model):
    _name = "receipt.kmitl.payment.method"
    _description = "Receipt Payment Method"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', 'in', ('cash', 'bank'))]",
        help="Journal used for the receipt's journal entry.",
    )
    account_id = fields.Many2one(
        "account.account",
        string="Debit Account",
        required=True,
        domain="[('deprecated', '=', False)]",
        help="GL account debited when a receipt using this payment method is "
             "posted (e.g. cash on hand, bank clearing).",
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ("name_unique", "unique(name, company_id)", "Payment method name must be unique."),
    ]
