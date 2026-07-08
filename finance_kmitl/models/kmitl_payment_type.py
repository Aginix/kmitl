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
    override_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Override Account",
        help="Override the destination account. Leave empty to use partner's default.",
    )
    is_cheque = fields.Boolean(
        string="Paid/Received by Cheque",
        help="Payments of this type are settled by cheque. They are exempt from "
        "the bank-export gate and post directly, and a cheque is added to the "
        "cheque control register when the payment is posted.",
    )

