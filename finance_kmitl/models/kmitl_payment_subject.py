# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class KmitlPaymentSubject(models.Model):
    """Payment subject (เรื่องที่จ่าย) — what an outbound payment is for.

    The subject drives *how the paying bank is chosen* (bank policy) and the
    default payment method, so the disbursement auditor only has to pick one
    subject per request and adjust the exception lines:

    - ``fixed``: every payment pays from the subject's configured journal
      (e.g. salary → KTB because staff must hold a KTB account; direct vendor
      payments → SCB, cross-bank routing is the bank system's job).
    - ``payee_bank``: each payee is paid from the institute's journal at the
      payee's own bank (e.g. เงินยืม/สำรองจ่าย), matched by the bank of the
      payee's account against the bank of each bank journal.
    """

    _name = "kmitl.payment.subject"
    _description = "KMITL Payment Subject (เรื่องที่จ่าย)"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    bank_policy = fields.Selection(
        selection=[
            ("fixed", "ธนาคารตายตัว"),
            ("payee_bank", "ตามธนาคารผู้รับ"),
        ],
        string="Bank Policy",
        required=True,
        default="fixed",
        help="How the paying bank (หัวจ่าย) is chosen: a fixed journal for "
        "every payment, or the institute's journal at each payee's own bank.",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Paying Journal",
        domain="[('type', '=', 'bank')]",
        help="The paying bank for the 'fixed' policy. Also the journal cheques "
        "are drawn on.",
    )
    default_method = fields.Selection(
        selection=[
            ("transfer", "เงินโอน"),
            ("cheque", "เช็ค"),
        ],
        string="Default Method",
        required=True,
        default="transfer",
        help="Default payment method applied to every request line; the "
        "auditor can override individual lines.",
    )
