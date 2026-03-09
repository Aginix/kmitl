# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class KmitlPaymentType(models.Model):
    _name = "kmitl.payment.type"
    _description = "KMITL Payment Type"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    direction = fields.Selection(
        selection=[
            ("inbound", "รับเงิน"),
            ("outbound", "จ่ายเงิน"),
        ],
        string="Direction",
        required=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain="[('type', 'in', ('bank', 'cash'))]",
        help="Default journal for this payment type. Leave empty to use the default.",
    )
    receivable_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Receivable Account",
        help="Override the receivable account. Leave empty to use partner's default.",
    )
    payable_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Payable Account",
        help="Override the payable account. Leave empty to use partner's default.",
    )

