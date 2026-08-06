# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class KmitlPaymentType(models.Model):
    """What a payment *is for* — the counterpart side of the entry.

    Every payment writes one entry with two sides and each has its own master
    data. The money side (out of which account, by which means, under which
    voucher) is the journal's payment method line — หัวจ่าย. This model owns the
    other side: which receivable, payable or deposit liability the money settles
    or creates. That is why ``advance_payment`` and ``purchase_guarantee`` add
    records of their own (เงินยืม, หลักประกัน) while nothing here describes how
    money moves any more.
    """

    _name = "kmitl.payment.type"
    _description = "KMITL Payment Purpose"
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
        string="Default Voucher",
        help="ใบสำคัญ this kind of operation is normally recorded under, for "
        "payments that are not driven by a paying account (a guarantee receipt, "
        "an advance). When a paying account is chosen it wins, because a paying "
        "account belongs to exactly one voucher journal.",
    )
    override_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Override Account",
        help="Override the destination account. Leave empty to use partner's default.",
    )
