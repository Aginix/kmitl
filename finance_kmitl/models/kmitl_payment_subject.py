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

    A paying account already names its method, so the method here is what
    **disambiguates** the allowed set: the same bank can hold a transfer paying
    account and a cheque one, and auto-matching a payee's bank has to know which
    of the two this subject means.

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
    default_payment_type_id = fields.Many2one(
        comodel_name="kmitl.payment.type",
        string="Default Method",
        required=True,
        domain="[('direction', '=', 'outbound')]",
        help="วิธีจ่าย this subject is normally paid by. It picks which of the "
        "allowed paying accounts apply — the auditor overrides by choosing a "
        "paying account of another method.",
    )
    auto_match_payee_bank = fields.Boolean(
        string="Auto-match by Payee's Bank",
        help="จับคู่หัวจ่ายตามธนาคารผู้รับ — pay each payee from the allowed "
        "account held at the bank of their own bank account; a payee whose "
        "bank matches none of them is paid from the fallback account. When "
        "off, every payee is paid from the main paying account.",
    )
    default_paying_account_id = fields.Many2one(
        comodel_name="kmitl.paying.account",
        string="Main / Fallback Paying Account",
        help="With auto-match off: the one account (หัวจ่ายหลัก) every payee "
        "is paid from. With auto-match on: the fallback (หัวจ่ายสำรอง) for a "
        "payee whose bank matches no allowed account. Left empty, the "
        "institute-wide default on the company applies.",
    )
    allowed_paying_account_ids = fields.Many2many(
        comodel_name="kmitl.paying.account",
        relation="kmitl_payment_subject_paying_account_rel",
        column1="subject_id",
        column2="paying_account_id",
        string="Allowed Paying Accounts",
        help="หัวจ่ายที่อนุญาต — the accounts auto-match may pick from, one "
        "per bank per method.",
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

    @api.constrains("default_paying_account_id", "default_payment_type_id")
    def _check_default_account_method(self):
        """The main/fallback account has to be able to pay the subject's way.

        A cheque subject falling back to a transfer account would pay the wrong
        way out of the wrong GL, and nothing downstream would notice.
        """
        for subject in self:
            account = subject.default_paying_account_id
            if (
                account
                and account.payment_type_id != subject.default_payment_type_id
            ):
                raise ValidationError(
                    _(
                        "The main/fallback paying account of '%(subject)s' is "
                        "%(account_method)s but the subject is paid by "
                        "%(subject_method)s.",
                        subject=subject.name,
                        account_method=account.payment_type_id.name,
                        subject_method=subject.default_payment_type_id.name,
                    )
                )

    def _paying_account_for_bank(self, bank, company=None):
        return self._paying_account_with_match(bank, company=company)[0]

    def _paying_account_with_match(self, bank, company=None):
        """Return ``(paying account, match)`` for a payee banking at ``bank``.

        With auto-match on, a payee banking with one of the allowed paying
        banks is paid from the account held there (match ``bank``); everyone
        else falls to the subject's fallback account (match ``fallback``).
        With auto-match off every payee is paid from the main account (match
        ``main``). A subject that leaves the account empty inherits the
        institute-wide default on the company, so the general rule is stated
        once and a subject only overrides when it differs (e.g. salary pays
        from the KTB account only).

        The match code is recorded on the disbursement line so the auditor can
        see which payees fell to the fallback and double-check them.

        Only the allowed accounts of the subject's own method are candidates: a
        bank may hold both a transfer and a cheque paying account, and matching
        on the bank alone would pick whichever came first.
        """
        self.ensure_one()
        allowed = self.allowed_paying_account_ids.filtered(
            lambda a: a.payment_type_id == self.default_payment_type_id
        )
        if self.auto_match_payee_bank and bank:
            match = allowed.filtered(lambda a: a.bank_id == bank)
            if match:
                return match[0], "bank"
        how = "fallback" if self.auto_match_payee_bank else "main"
        if self.default_paying_account_id:
            return self.default_paying_account_id, how
        company = company or self.env.company
        if company.default_paying_account_id and (
            not allowed or company.default_paying_account_id in allowed
        ):
            return company.default_paying_account_id, how
        return allowed[:1], how
