# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ReceiptPaymentMethod(models.Model):
    _name = "kmitl.payment.method"
    _description = "Receipt Payment Method"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    payment_type = fields.Selection(
        [
            ("cash", "Cash"),
            ("cheque", "Cheque"),
            ("transfer", "Money Transfer"),
            ("other", "Other"),
        ],
        string="Payment Type",
        required=True,
        default="cash",
        help="Drives which box is ticked on the printed official receipt.",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        check_company=True,
        domain="[('type', 'in', ('cash', 'bank')), ('company_id', 'in', allowed_company_ids)]",
        help="Journal used for the receipt's journal entry.",
    )
    account_id = fields.Many2one(
        "account.account",
        string="Debit Account",
        required=True,
        check_company=True,
        domain="[('deprecated', '=', False), ('company_id', 'in', allowed_company_ids)]",
        help="GL account debited when a receipt using this payment method is "
             "posted (e.g. cash on hand, bank clearing).",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ("name_unique", "unique(name, company_id)", "Payment method name must be unique."),
    ]
