# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class KmitlPaymentType(models.Model):
    """ประเภทธุรกรรม — the counterpart side of a payment entry.

    What the money *is*: which receivable, payable or deposit liability it
    settles or creates (เงินรับฝากค้ำประกัน, เงินยืม, …), expressed through the
    override account. It says nothing about how money moves — that is the paying
    account's business (`account.payment.method.line`, หัวจ่าย), which names its
    own method. A flag here describing the money side would be a second, rival
    answer to the same question, so there is none.

    Not to be confused with ``kmitl.payment.subject`` (เรื่องที่จ่าย — which
    paying account a disbursement's payees are served from).
    """

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
        string="Default Voucher",
        domain="[('type', 'in', ('bank', 'cash'))]",
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
