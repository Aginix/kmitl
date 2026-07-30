# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class KmitlPaymentSubject(models.Model):
    """Payment subject (เรื่องที่จ่าย) — what an outbound payment is for.

    A subject answers two questions for the disbursement auditor, so that
    picking one subject per request is normally all that is needed:

    - *how* it is paid — the default payment method (เงินโอน / เช็ค / เงินสด);
    - *out of which account* — a default paying account (หัวจ่าย) plus the set
      of accounts allowed for this subject.

    The allowed set is what makes the real cases fall out of one mechanism:
    salary allows only the KTB account; a staff advance allows all four bank
    accounts and each payee is served from the account at their own bank;
    direct vendor payments allow only the SCB account.
    """

    _name = "kmitl.payment.subject"
    _description = "KMITL Payment Subject (เรื่องที่จ่าย)"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    default_method = fields.Selection(
        selection=[
            ("transfer", "เงินโอน"),
            ("cheque", "เช็ค"),
            ("cash", "เงินสด"),
        ],
        string="Default Method",
        required=True,
        default="transfer",
        help="Payment method applied to every request line by default; the "
        "auditor can override individual lines.",
    )
    default_paying_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Default Paying Account",
        domain="[('is_paying_account', '=', True)]",
        help="หัวจ่ายตั้งต้น — used for a payee whose own bank is not among "
        "the allowed accounts.",
    )
    allowed_paying_account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="kmitl_payment_subject_paying_account_rel",
        column1="subject_id",
        column2="account_id",
        string="Allowed Paying Accounts",
        domain="[('is_paying_account', '=', True)]",
        help="หัวจ่ายที่อนุญาต — the accounts this subject may be paid from. "
        "With more than one, each payee is served from the account held at "
        "their own bank, falling back to the default.",
    )

    @api.onchange("default_paying_account_id")
    def _onchange_default_paying_account_id(self):
        """The default must be usable, so keep it inside the allowed set."""
        if (
            self.default_paying_account_id
            and self.default_paying_account_id
            not in self.allowed_paying_account_ids
        ):
            self.allowed_paying_account_ids |= self.default_paying_account_id

    @api.constrains("default_paying_account_id", "allowed_paying_account_ids")
    def _check_default_is_allowed(self):
        for subject in self:
            if (
                subject.default_paying_account_id
                and subject.allowed_paying_account_ids
                and subject.default_paying_account_id
                not in subject.allowed_paying_account_ids
            ):
                raise ValidationError(
                    _(
                        "The default paying account of '%s' must be one of its "
                        "allowed paying accounts."
                    )
                    % subject.name
                )

    def _paying_account_for_bank(self, bank):
        """Return the allowed paying account held at ``bank``, else the default.

        This is what serves a staff advance out of the payee's own bank without
        any extra policy switch: allow the four bank accounts and the payee's
        bank decides, while a subject that allows a single account always
        returns that one.
        """
        self.ensure_one()
        allowed = self.allowed_paying_account_ids
        if bank:
            match = allowed.filtered(lambda a: a.paying_bank_id == bank)
            if match:
                return match[0]
        if self.default_paying_account_id:
            return self.default_paying_account_id
        return allowed[:1]
