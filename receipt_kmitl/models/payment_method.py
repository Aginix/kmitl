# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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
        string="Cash Account",
        required=True,
        check_company=True,
        domain="[('deprecated', '=', False), ('company_id', 'in', allowed_company_ids)]",
        help="GL account debited against each revenue line when a receipt "
             "using this payment method is posted (e.g. cash on hand).",
    )
    deposit_account_id = fields.Many2one(
        "account.account",
        string="Deposit Bank Account",
        required=True,
        check_company=True,
        domain="[('deprecated', '=', False), ('company_id', 'in', allowed_company_ids)]",
        help="Bank account the cash is remitted to. Debited for the "
             "receipt's full total against the Cash Account, in the same "
             "journal entry.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ("name_unique", "unique(name, company_id)", "Payment method name must be unique."),
    ]

    @api.constrains("account_id", "deposit_account_id")
    def _check_deposit_account_differs(self):
        for rec in self:
            if rec.account_id == rec.deposit_account_id:
                raise ValidationError(
                    _("Cash Account and Deposit Bank Account must be different.")
                )
