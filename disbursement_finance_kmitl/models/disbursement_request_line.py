# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    payment_method = fields.Selection(
        selection=[
            ("transfer", "เงินโอน"),
            ("cheque", "เช็ค"),
            ("cash", "เงินสด"),
        ],
        string="Payment Method",
        copy=False,
        help="How this payee is paid. Defaulted from the request's payment "
        "subject by the auditor; lines of the same payee must share one "
        "method (one bill per payee, paid in full by one payment).",
    )
    paying_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Paying Account",
        domain="[('is_paying_account', '=', True)]",
        copy=False,
        help="หัวจ่าย — the account the money leaves from. Defaulted from the "
        "request's payment subject (the account at the payee's own bank when "
        "the subject allows several); lines of the same payee must share one.",
    )
