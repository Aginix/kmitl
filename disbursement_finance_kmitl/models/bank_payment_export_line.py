# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class BankPaymentExportLine(models.Model):
    _inherit = "bank.payment.export.line"

    # Not prefixed ``payment_`` like the base's related columns
    # (``payment_partner_id``, ``payment_amount``): that prefix exists because a row
    # has a partner and an amount of its own to be confused with, and the ใบขอเบิก
    # has no such rival here.
    disbursement_request_id = fields.Many2one(
        related="payment_id.disbursement_request_id",
        string="Disbursement Request",
        # Pinned, because the row tree is ``editable="bottom"`` and a related field
        # writes through: without this, an e-payment officer could re-point a
        # voucher at another ใบขอเบิก from inside a file. Which request a voucher
        # was raised for is decided where the voucher is raised — the same reason
        # ``payment_partner_bank_id`` is pinned in ``finance_kmitl``.
        readonly=True,
        help="The ใบขอเบิก this payee's voucher was raised for. Shown per row "
        "because a file commonly carries several requests, and the header's own "
        "trail can only name one.",
    )
