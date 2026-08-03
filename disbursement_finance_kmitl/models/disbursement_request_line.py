# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


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
        "the subject auto-matches); lines of the same payee must share one.",
    )
    paying_account_match = fields.Selection(
        selection=[
            ("bank", "ตรงธนาคารผู้รับ"),
            ("fallback", "ใช้หัวจ่ายสำรอง"),
            ("main", "หัวจ่ายหลัก"),
            ("manual", "เลือกเอง"),
        ],
        string="Match Result",
        copy=False,
        readonly=True,
        help="How the paying account was chosen, so the auditor can spot the "
        "payees that fell to the fallback and double-check them. Editing the "
        "paying account by hand marks the line as chosen manually.",
    )

    @api.onchange("paying_account_id")
    def _onchange_paying_account_id(self):
        """A hand-picked account is provenance of its own.

        Only fires from the UI: the subject-derived assignment writes through
        the ORM, which does not run onchange, so it never mislabels itself.
        """
        for line in self:
            line.paying_account_match = (
                "manual" if line.paying_account_id else False
            )
