# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


def _paying_account_domain(self):
    """The paying accounts (หัวจ่าย) a subject may name.

    They hang off ใบสำคัญจ่าย (PV) — the voucher a disbursement is paid on, whose
    sequence *is* the voucher number. The other voucher journals have money
    accounts of their own (PVR returns a loan, PAR disburses one) but they are
    not หัวจ่าย for this flow, and choosing one would number a disbursement
    payment as a loan voucher.
    """
    journal = self.env.ref("account_kmitl.journal_pv", raise_if_not_found=False)
    domain = [
        ("payment_type", "=", "outbound"),
        ("payment_account_id", "!=", False),
    ]
    if journal:
        domain.append(("journal_id", "=", journal.id))
    return domain


class KmitlPaymentSubject(models.Model):
    """Payment subject (เรื่องที่จ่าย) — what an outbound payment is for.

    A subject answers, once per disbursement request, "out of which account do
    these payees get paid": it names a paying account (หัวจ่าย) and, when the
    treasury office serves each payee from the account held at their own bank,
    the set of accounts that may be matched against.

    It does **not** decide how a payee is paid. A paying account already names
    its method, so choosing the account chooses the method, and the auditor is
    free to move a single payee onto a cheque or cash account without the
    subject having to agree — payees of one request genuinely are paid different
    ways. The method the subject carries exists for one purpose only: to say
    *which* of a bank's paying accounts auto-matching means, since one current
    account can be both transferred from and drawn cheques on.

    Not to be confused with ``kmitl.payment.type`` (ประเภทธุรกรรม — the
    counterpart side: what the money *is*) nor with
    ``disbursement.request.payment_type`` (direct/advance/prepaid, inherited from
    the approval request).
    """

    _name = "kmitl.payment.subject"
    _description = "KMITL Payment Subject (เรื่องที่จ่าย)"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    default_payment_method_id = fields.Many2one(
        comodel_name="account.payment.method",
        string="Default Method",
        required=True,
        domain="[('payment_type', '=', 'outbound')]",
        help="วิธีจ่าย this subject is normally paid by. It says which of a "
        "bank's paying accounts auto-matching means — it does not restrict what "
        "the auditor may choose for an individual payee.",
    )
    auto_match_payee_bank = fields.Boolean(
        string="Auto-match by Payee's Bank",
        help="จับคู่หัวจ่ายตามธนาคารผู้รับ — pay each payee from the allowed "
        "account held at the bank of their own bank account; a payee whose bank "
        "matches none of them is paid from the fallback account. When off, "
        "every payee is paid from the main paying account.",
    )
    default_paying_account_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Main / Fallback Paying Account",
        required=True,
        domain=_paying_account_domain,
        help="With auto-match off: the one account (หัวจ่ายหลัก) every payee is "
        "paid from. With auto-match on: the fallback (หัวจ่ายสำรอง) for a payee "
        "whose bank matches no allowed account.",
    )
    allowed_paying_account_ids = fields.Many2many(
        comodel_name="account.payment.method.line",
        relation="kmitl_payment_subject_paying_account_rel",
        column1="subject_id",
        column2="paying_account_id",
        string="Allowed Paying Accounts",
        domain=_paying_account_domain,
        help="หัวจ่ายที่อนุญาต — what a payee of this subject may be paid from, "
        "and what auto-match picks between. Left empty, any paying account may "
        "be chosen by hand.",
    )

    @api.onchange("default_paying_account_id")
    def _onchange_default_paying_account_id(self):
        """The default must be usable, so keep it inside the allowed set."""
        if (
            self.default_paying_account_id
            and self.allowed_paying_account_ids
            and self.default_paying_account_id not in self.allowed_paying_account_ids
        ):
            self.allowed_paying_account_ids |= self.default_paying_account_id

    @api.constrains("default_paying_account_id", "allowed_paying_account_ids")
    def _check_default_is_allowed(self):
        for subject in self:
            if (
                subject.allowed_paying_account_ids
                and subject.default_paying_account_id
                not in subject.allowed_paying_account_ids
            ):
                raise ValidationError(
                    _(
                        "The main/fallback paying account of '%s' must be one "
                        "of its allowed paying accounts."
                    )
                    % subject.name
                )

    @api.constrains("default_paying_account_id", "default_payment_method_id")
    def _check_default_account_method(self):
        """The main/fallback account has to pay the subject's way.

        A cheque subject falling back to a transfer account would pay the wrong
        way out of the wrong GL, and nothing downstream would notice.
        """
        for subject in self:
            account = subject.default_paying_account_id
            if account.payment_method_id != subject.default_payment_method_id:
                raise ValidationError(
                    _(
                        "The main/fallback paying account of '%(subject)s' is "
                        "%(account_method)s but the subject is paid by "
                        "%(subject_method)s.",
                        subject=subject.name,
                        account_method=account.payment_method_id.name,
                        subject_method=subject.default_payment_method_id.name,
                    )
                )

    @api.constrains(
        "auto_match_payee_bank",
        "allowed_paying_account_ids",
        "default_payment_method_id",
    )
    def _check_auto_match_has_candidates(self):
        """Auto-matching with nothing to match against silently sends every
        payee to the fallback, which reads on screen as if the bank matched."""
        for subject in self:
            if not subject.auto_match_payee_bank:
                continue
            if not subject._match_candidates():
                raise ValidationError(
                    _(
                        "'%s' matches the payee's bank but lists no allowed "
                        "paying account paid that way, so every payee would "
                        "fall to the fallback."
                    )
                    % subject.name
                )

    def _match_candidates(self):
        """The allowed accounts auto-match may pick between.

        Narrowed to the subject's own method: a bank may hold both a transfer
        and a cheque paying account, and matching on the bank alone would take
        whichever came first.
        """
        self.ensure_one()
        return self.allowed_paying_account_ids.filtered(
            lambda account: account.payment_method_id == self.default_payment_method_id
        )

    def _paying_account_with_match(self, bank):
        """Return ``(paying account, match)`` for a payee banking at ``bank``.

        With auto-match on, a payee banking with one of the allowed paying banks
        is paid from the account held there (match ``bank``); everyone else falls
        to the subject's account (match ``fallback``). With auto-match off every
        payee is paid from that same account (match ``main``) — one field, two
        roles, the label following the flag.

        The match is recorded on the payment line so the auditor can see which
        payees fell to the fallback and double-check exactly those.
        """
        self.ensure_one()
        if self.auto_match_payee_bank and bank:
            matched = self._match_candidates().filtered(
                lambda account: account.bank_id == bank
            )
            if matched:
                return matched[0], "bank"
        return (
            self.default_paying_account_id,
            "fallback" if self.auto_match_payee_bank else "main",
        )
