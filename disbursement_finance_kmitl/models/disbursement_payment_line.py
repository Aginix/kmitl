# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# The banking coordinates a person may correct: out of which account (which
# names the method too) and into which account. Never who is paid, never how
# much.
BANKING_FIELDS = ("paying_account_id", "partner_bank_id")


class DisbursementPaymentLine(models.Model):
    """One payee, one payment (รายการจ่ายเงิน).

    A request line (``disbursement.request.line``) is one *item* being
    reimbursed, so a payee with three receipts has three of them. This is the
    payee-level row that becomes exactly one ``account.payment`` against
    exactly one posted bill — which is why the payment axes (method, paying
    account) live here rather than on the request line: there, the same
    decision had to be copied onto every item of a payee and then validated
    back into agreement. Here the invariant is structural.

    The amounts are read from the **posted bill** — the money that will
    actually leave, net of withholding tax — not from the sum of the request
    lines, which is only what was asked for.
    """

    _name = "disbursement.payment.line"
    _description = "Disbursement Payment Line (รายการจ่ายเงิน)"
    _order = "id"

    request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    bill_id = fields.Many2one(
        comodel_name="account.move",
        string="Vendor Bill",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        related="bill_id.partner_id",
        string="Payee",
        store=True,
    )
    company_id = fields.Many2one(
        related="request_id.company_id",
        store=True,
    )
    currency_id = fields.Many2one(
        related="bill_id.currency_id",
        store=True,
    )

    # ------------------------------------------------------------------
    # Banking coordinates (set by the auditor, correctable by finance)
    # ------------------------------------------------------------------
    partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Recipient Bank",
        copy=False,
        help="The payee's account the money is transferred into. Defaulted "
        "from the bill; it is what the payment and the bank export carry.",
    )
    paying_account_id = fields.Many2one(
        comodel_name="kmitl.paying.account",
        string="Paying Account",
        domain="[('id', 'in', allowed_paying_account_ids)]",
        copy=False,
        help="หัวจ่าย — the account the money leaves from, which names the "
        "payment method too. Defaulted from the request's payment subject (the "
        "account at the payee's own bank when the subject auto-matches).",
    )
    payment_type_id = fields.Many2one(
        related="paying_account_id.payment_type_id",
        string="Payment Method",
        readonly=True,
        help="วิธีจ่าย — a property of the chosen paying account rather than a "
        "second choice, so the two cannot contradict each other.",
    )
    allowed_paying_account_ids = fields.Many2many(
        comodel_name="kmitl.paying.account",
        string="Allowed Paying Accounts",
        compute="_compute_allowed_paying_account_ids",
        help="What the paying account may be set to, so the subject's policy "
        "is enforced while choosing instead of rejected afterwards.",
    )
    paying_account_match = fields.Selection(
        selection=[
            ("bank", "ตรงธนาคารผู้รับ"),
            ("fallback", "ไม่ตรงกับหัวจ่ายหลัก"),
            ("main", "หัวจ่ายหลัก"),
            ("manual", "เลือกเอง"),
        ],
        string="Match Result",
        copy=False,
        readonly=True,
        help="The provenance of the paying account, so the payees that fell to "
        "the fallback can be spotted and double-checked. Picking the account by "
        "hand marks the row as chosen manually.",
    )

    # ------------------------------------------------------------------
    # Amounts (from the bill, frozen once a payment owns them)
    # ------------------------------------------------------------------
    amount_bill = fields.Monetary(
        string="Bill Amount",
        readonly=True,
        copy=False,
        currency_field="currency_id",
    )
    amount_wht = fields.Monetary(
        string="Withholding Tax",
        readonly=True,
        copy=False,
        currency_field="currency_id",
    )
    amount_net = fields.Monetary(
        string="Net Amount to Pay",
        readonly=True,
        copy=False,
        currency_field="currency_id",
        help="What actually leaves the bank for this payee.",
    )

    payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Payment",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    _sql_constraints = [
        (
            "bill_uniq",
            "unique(bill_id)",
            "A bill can only be paid by one payment line.",
        ),
    ]

    def name_get(self):
        """A row is known by its payee — that is what the chatter trail of
        changes has to read as."""
        return [
            (line.id, line.partner_id.display_name or _("Payment Line"))
            for line in self
        ]

    # ------------------------------------------------------------------
    # Derivation
    # ------------------------------------------------------------------
    @api.depends("request_id.payment_subject_id.allowed_paying_account_ids")
    def _compute_allowed_paying_account_ids(self):
        """A subject that lists allowed accounts narrows the choice to them;
        a subject that lists none allows every paying account.

        The list spans methods on purpose: switching a payee from เงินโอน to
        เช็ค *is* picking a different paying account.
        """
        every = self.env["kmitl.paying.account"].search([])
        for line in self:
            allowed = (
                line.request_id.payment_subject_id.allowed_paying_account_ids
            )
            line.allowed_paying_account_ids = allowed or every

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

    @api.onchange("partner_bank_id")
    def _onchange_partner_bank_id(self):
        """Re-derive the paying account when the payee's bank changes.

        The derivation has two inputs — the subject and the payee's own bank —
        so a new bank makes an auto-matched paying account, and the green badge
        that says it matches, a lie. Rows a person picked by hand are left
        alone: they already carry a decision.
        """
        for line in self:
            subject = line.request_id.payment_subject_id
            if not subject.auto_match_payee_bank:
                continue
            if line.paying_account_match == "manual":
                continue
            account, match = subject._paying_account_with_match(
                line.partner_bank_id.bank_id, company=line.company_id
            )
            line.paying_account_id = account
            line.paying_account_match = match if account else False

    # ------------------------------------------------------------------
    # Amounts
    # ------------------------------------------------------------------
    def _payment_amount_vals(self):
        """Return ``(bill amount, WHT deduction, write-off line values)``.

        The single place the money is worked out, so the row the finance office
        reviews and the payment that leaves the bank cannot disagree.
        """
        self.ensure_one()
        bill = self.bill_id
        amount = abs(bill.amount_residual)
        amount_wht = 0.0
        write_off_line_vals = []
        wht_lines = bill.line_ids.filtered("wht_tax_id")
        if wht_lines:
            deduction_list, deducted = wht_lines._prepare_deduction_list(
                fields.Date.context_today(self), bill.currency_id
            )
            if deduction_list and deducted:
                amount_wht = deducted
                for deduct in deduction_list:
                    write_off_line_vals.append({
                        "name": deduct["name"],
                        "account_id": deduct["account_id"],
                        "partner_id": bill.partner_id.id,
                        "currency_id": bill.currency_id.id,
                        "amount_currency": -deduct["amount"],
                        "balance": -deduct["amount"],
                        "wht_tax_id": deduct["wht_tax_id"],
                        "tax_base_amount": deduct["wht_amount_base"],
                    })
        return amount, amount_wht, write_off_line_vals

    def _refresh_amounts(self):
        """Re-read the amounts from the bill.

        Rows a payment already owns are skipped: the bill's residual drops to
        zero the moment the payment posts (clearing), so a closed request would
        otherwise report that nothing was ever paid. The amounts freeze at the
        same moment the banking coordinates do.
        """
        for line in self.filtered(lambda l: not l.payment_id):
            amount, amount_wht, _write_off = line._payment_amount_vals()
            line.write({
                "amount_bill": amount,
                "amount_wht": amount_wht,
                "amount_net": amount - amount_wht,
            })
        return True

    # ------------------------------------------------------------------
    # Editability guard
    # ------------------------------------------------------------------
    def _banking_editable(self):
        """A row's banking coordinates are editable exactly while no payment
        contradicts them: the auditor's during Payment Audit, the finance
        office's during Payment Review, nobody's once the payment exists.

        Phrased against the payment rather than against a list of states, so it
        stays true if the workflow grows another step.
        """
        self.ensure_one()
        state = self.request_id.state
        if state == "bills_posted":
            return True
        if state == "payment_authorized":
            return not self.payment_id
        return False

    def write(self, vals):
        if any(field in vals for field in BANKING_FIELDS):
            for line in self:
                if not line._banking_editable():
                    raise UserError(
                        _(
                            "The payment of %(payee)s can no longer be "
                            "changed: %(reason)s",
                            payee=line.partner_id.display_name,
                            reason=(
                                _("its payment %s already exists.")
                                % line.payment_id.display_name
                                if line.payment_id
                                else _(
                                    "the request is not open for audit or "
                                    "payment review."
                                )
                            ),
                        )
                    )
        return super().write(vals)
