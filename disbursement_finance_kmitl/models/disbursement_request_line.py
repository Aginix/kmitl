# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    payment_method = fields.Selection(
        selection=[
            ("transfer", "เงินโอน"),
            ("cheque", "เช็ค"),
        ],
        string="Payment Method",
        copy=False,
        help="How this payee is paid. Defaulted from the request's payment "
        "subject by the auditor; lines of the same payee must share one "
        "method (one bill per payee, paid in full by one payment).",
    )
