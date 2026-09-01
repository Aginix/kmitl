# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class BankPaymentExport(models.Model):
    _name = "bank.payment.export"
    _inherit = ["bank.payment.export", "thai.date.mixin"]
    # The upstream model leaves _order unset, so the register opened on id ASC —
    # the oldest file first, which is the wrong end for a register that is read
    # to find the run just made. The sequence is fixed-width (PE<yy>#####) and
    # minted at create, so ordering by it lexically is ordering by recency.
    _order = "name desc"

    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        store=True,
        compute="_compute_date_range_fy",
        search="_search_date_range_fy",
    )
    # Not `required=True`. The rule is KMITL's — "one file debits one account" — and
    # the field is on a model the localisation owns, so a NOT NULL column imposes it
    # on every other module's exports too: the BAY, KBANK, KTB and upstream suites
    # all create a file with no paying account and would fail at setup. It is
    # enforced where it can be acted on instead — required on this office's own form,
    # refused by `action_get_all_payments` (which is the real hazard: without one, the
    # picker has nothing to narrow by and pulls in every paying account's vouchers),
    # and re-checked at confirmation.
    paying_account_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Paying Account",
        domain="[('payment_type', '=', 'outbound'), "
        "('payment_method_id.code', '=', 'kmitl_transfer'), "
        "('bank_account_id', '!=', False)]",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
        help="The account this file debits. One file is uploaded to one bank "
        "and debits one account, so it is chosen first and the payments that "
        "can be picked into the file are narrowed to the ones paid from it.",
    )
    # 'done' says the file exists; this says the money arrived. Appended rather
    # than renaming 'done', so nothing already reading it changes meaning — see
    # ADR-0004.
    state = fields.Selection(
        selection_add=[("paid", "Paid")],
        ondelete={"paid": "set default"},
    )
    other_draft_export_ids = fields.Many2many(
        comodel_name="bank.payment.export",
        compute="_compute_other_draft_export_ids",
        string="Other Draft Files",
        help="The other draft files debiting this paying account. Not an error — "
        "two files differing only by effective date are a normal way to hold an "
        "urgent batch apart from the month's run — but worth naming, so a second "
        "one is deliberate rather than a forgotten first one.",
    )
    export_line_count = fields.Integer(
        compute="_compute_export_line_count",
        string="Rows",
    )
    transfer_proof_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="bank_payment_export_transfer_proof_rel",
        column1="export_id",
        column2="attachment_id",
        string="Transfer Proof",
        copy=False,
        help="What the bank sent back once the file had been uploaded — a slip, a "
        "statement page, a screen. It has a field of its own because the exported "
        "file is attached to this record too, and the office is being asked for the "
        "opposite document: not what the bank was told to do, but what it did. "
        "Anything attached here is also listed with the record's other attachments.",
    )
    epayment_note = fields.Text(
        string="Transfer Note",
        copy=False,
        readonly=True,
        help="Written when the transfer is confirmed. The file is confirmed as a "
        "whole, so this is where a payee the bank could not credit — and how they "
        "were settled outside the system instead — is recorded.",
    )

    # -------------------------------------------------------------------------
    # Fiscal year
    # -------------------------------------------------------------------------
    @api.depends("effective_date", "company_id")
    def _compute_date_range_fy(self):
        for rec in self:
            date = fields.Date.to_date(rec.effective_date)
            company = rec.company_id
            rec.account_fiscal_year_id = (
                company and date and company.find_daterange_fy(date) or False
            )

    @api.model
    def _search_date_range_fy(self, operator, value):
        if operator in ("=", "!=", "in", "not in"):
            date_range_domain = [("id", operator, value)]
        else:
            date_range_domain = [("name", operator, value)]
        date_ranges = self.env["account.fiscal.year"].search(date_range_domain)
        domain = [("id", "=", -1)]
        for date_range in date_ranges:
            domain = expression.OR(
                [
                    domain,
                    [
                        "&",
                        ("effective_date", ">=", date_range.date_from),
                        ("effective_date", "<=", date_range.date_to),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", date_range.company_id.id),
                    ],
                ]
            )
        return domain

    # -------------------------------------------------------------------------
    # Paying account (หัวจ่าย): the fact the whole file hangs off
    # -------------------------------------------------------------------------
    @api.depends("paying_account_id", "state")
    def _compute_other_draft_export_ids(self):
        for rec in self:
            rec.other_draft_export_ids = (
                rec._other_draft_exports()
                if rec.state == "draft" and rec.paying_account_id
                else False
            )

    @api.depends("export_line_ids")
    def _compute_export_line_count(self):
        for rec in self:
            rec.export_line_count = len(rec.export_line_ids)

    def _action_open_created(self):
        """Show what was just created: the file itself, or the list of files."""
        if len(self) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": self._name,
                "res_id": self.id,
                "view_mode": "form",
            }
        return {
            "name": _("e-Payment Files"),
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "tree,form",
            "domain": [("id", "in", self.ids)],
        }

    def _other_draft_exports(self):
        """The other draft files debiting this paying account."""
        self.ensure_one()
        return self.search(
            [
                ("id", "!=", self._origin.id or 0),
                ("state", "=", "draft"),
                ("paying_account_id", "=", self.paying_account_id.id),
            ]
        )

    def action_get_all_payments(self):
        """Refuse to pull anything until the file says which account it debits.

        This is where a missing paying account actually does damage: the picker's
        domain narrows by it, so without one the search matches every confirmed
        voucher of every หัวจ่าย, stamps them all, and only says so at confirmation —
        by which time the officer has a file to dismantle by hand.
        """
        for rec in self:
            if not rec.paying_account_id:
                raise UserError(
                    _(
                        "Choose the paying account of %s first. One file debits one "
                        "account, and it is what decides which vouchers can go in."
                    )
                    % rec.display_name
                )
        return super().action_get_all_payments()

    @api.model
    def _prepare_bank_vals_from_paying_account(self, paying_account):
        """The bank facts that follow from the account being debited.

        Both are facts about the paying account, not choices: the file goes to
        whichever bank holds it. Deriving them is what lets the officer open an
        empty file, name the หัวจ่าย and pull the vouchers, instead of filling in
        three fields that all follow from the first.

        The layout is only filled when the bank leaves no choice. Where a bank has
        more than one — KTB has both iPay and Direct Credit — picking for the
        officer would be guessing at which service the batch is going out under.

        The layout half is here for the **create** path only: the wizard builds
        files in code, where no onchange runs.
        ``l10n_th_bank_payment_export_format`` derives it on the form, listening on
        ``bank``, so ``_onchange_paying_account_id`` sets nothing but the bank and
        leaves the rest to it.

        Nothing is derived for a bank whose localisation module is not installed:
        ``bank`` is a selection each of those extends, so a BIC that no installed
        module has declared is not a value the field can hold. Setting it anyway
        would fail on a database that simply pays out of an account at a bank
        nobody has written a layout for yet.
        """
        bic = paying_account.bank_id.bic
        known = dict(self._fields["bank"]._description_selection(self.env))
        if not bic or bic not in known:
            return {}
        vals = {"bank": bic}
        formats = self.env["bank.export.format"].search([("bank", "=", bic)])
        if len(formats) == 1:
            vals["bank_export_format_id"] = formats.id
        return vals

    @api.onchange("paying_account_id")
    def _onchange_paying_account_id(self):
        """Set only the bank. The layout follows from it, one pass later.

        ``l10n_th_bank_payment_export_format`` listens on ``bank`` and does the
        rest — drops a layout belonging to the previous bank, and picks the new
        bank's if it has exactly one. Odoo runs onchanges in passes, so a ``bank``
        written here is picked up there, and this does not have to repeat it.
        """
        for rec in self:
            vals = rec._prepare_bank_vals_from_paying_account(rec.paying_account_id)
            if vals.get("bank"):
                rec.bank = vals["bank"]

    @api.constrains("bank", "paying_account_id")
    def _check_bank_matches_paying_account(self):
        """The file's bank has to be the bank that holds the paying account.

        The base constraint that meant to do this compares ``bank`` against the
        payment journal's bank, and a KMITL journal is a voucher type (ใบสำคัญ)
        holding no bank account at all (ADR-0001), so it reads an empty list and
        never fires. Nothing therefore stopped a file debiting a KTB account from
        being written in SCB's layout — the bank would reject the upload, and the
        officer would have no way to see why from the record.
        """
        for rec in self:
            bic = rec.paying_account_id.bank_id.bic
            if rec.bank and bic and rec.bank != bic:
                raise ValidationError(
                    _(
                        "%(account)s is held at %(account_bank)s, but this file is "
                        "written for %(file_bank)s. A file is uploaded to the bank "
                        "that holds the account it debits."
                    )
                    % {
                        "account": rec.paying_account_id.display_name,
                        "account_bank": rec.paying_account_id.bank_id.display_name,
                        "file_bank": dict(
                            rec._fields["bank"]._description_selection(self.env)
                        ).get(rec.bank, rec.bank),
                    }
                )

    # -------------------------------------------------------------------------
    # Overrides: accept submitted payments instead of posted
    # -------------------------------------------------------------------------
    def _transfer_payment_method(self):
        """The KMITL เงินโอน method — the only one an e-payment file carries."""
        return self.env.ref(
            "account_kmitl.payment_method_transfer_out",
            raise_if_not_found=False,
        )

    def _check_single_paying_account(self, payments):
        """One file is uploaded to one bank and debits one account.

        Checked against the payments rather than against the header field, so it
        holds however the batch was assembled — picking payments by hand,
        pulling every submitted one, or opening the export from a selection.
        """
        paying_accounts = payments.mapped("payment_method_line_id")
        if len(paying_accounts) > 1:
            raise UserError(
                _(
                    "One file debits one account, but these payments are paid "
                    "from %s. Export them separately, one paying account at a "
                    "time."
                )
                % ", ".join(paying_accounts.mapped("display_name"))
            )
        if paying_accounts and not paying_accounts.bank_account_id:
            raise UserError(
                _(
                    "%s names no bank account, so the file would carry no "
                    "sending account. Set it in Finance ▸ Settings ▸ Paying "
                    "Accounts."
                )
                % paying_accounts.display_name
            )
        return True

    def _check_constraint_confirm(self):
        """Also guard the batches assembled by pulling every submitted payment,
        which never pass through the create-from-selection check."""
        res = super()._check_constraint_confirm()
        for record in self:
            record._check_single_paying_account(
                record.export_line_ids.mapped("payment_id")
            )
        return res

    def _check_constraint_create_bank_payment_export(self, payments):
        """Replace the base check, which insists on posted Manual payments.

        Deliberately does not call super(): a KMITL file carries vouchers the
        *finance* office has confirmed for the bank and the accounting office has
        not booked yet, which the base rejects outright — it expects the entry to
        be posted first. The per-bank rules layered on top would be silenced by
        that, so they are invoked through their own hook.
        """
        self._check_bank_specific_constraint(payments)
        self._check_single_paying_account(payments)
        comment_template = payments[0].bank_payment_template_id
        previous_currency = False
        method_transfer_out = self._transfer_payment_method()
        for payment in payments:
            if not payment.needs_bank_export:
                raise UserError(
                    _(
                        "%s is settled outside the bank file (cheque or cash) "
                        "and cannot be exported."
                    )
                    % payment.name
                )
            if method_transfer_out and payment.payment_method_id != method_transfer_out:
                raise UserError(
                    _("You can export bank payments with the '%s' payment method only.")
                    % method_transfer_out.name
                )
            if payment.bank_payment_template_id != comment_template:
                raise UserError(
                    _("All payments must have the same bank payment template.")
                )
            if payment.export_status != "draft":
                raise UserError(_("Payments have been already exported."))
            if payment.finance_state != "confirmed":
                raise UserError(
                    _(
                        "%s is not confirmed for the bank, so it may still change "
                        "and cannot be put in a file."
                    )
                    % payment.display_name
                )
            if previous_currency and payment.currency_id != previous_currency:
                raise UserError(_("You can export bank payments with 1 currency only."))
            previous_currency = payment.currency_id

    # -------------------------------------------------------------------------
    # E-payment result confirmation (manual, whole batch)
    # -------------------------------------------------------------------------
    def _check_result_recordable(self):
        """A result can only be recorded once there was a file to upload.

        Nothing here is told by a bank, so every one of these is a person's word
        about what happened after they uploaded the file. Before the file exists
        there is nothing they could have seen.
        """
        for rec in self:
            if rec.state not in ("done", "paid"):
                raise UserError(
                    _(
                        "%s has not been exported yet, so there is no bank result "
                        "to record against it."
                    )
                    % rec.display_name
                )
        return True

    def _rows_with_a_result_to_give(self):
        """The rows a blanket result may speak for.

        A rejected row was taken out of the file and its payment released, so it is
        no longer one of the payees this file paid — saying anything about its
        outcome here would put a result on a voucher that may already be in another
        file.
        """
        return self.mapped("export_line_ids").filtered(
            lambda line: line.state != "reject"
        )

    def action_mark_all_epayment_success(self):
        self._check_result_recordable()
        self._rows_with_a_result_to_give()._apply_epayment_result("success")

    def action_mark_all_epayment_failed(self):
        self._check_result_recordable()
        self._rows_with_a_result_to_give()._apply_epayment_result("failed")

    def _check_transfer_proof(self):
        """A file is not closed on somebody's memory of having uploaded it.

        The exported file is kept on this record too, so "has an attachment" would
        be true from the moment it was produced and would gate nothing. The proof
        the office is asked for is what came *back* — the bank's confirmation — and
        it has a field of its own so the two can never be mistaken for each other.
        """
        for rec in self:
            if not rec.transfer_proof_ids:
                # Kept to two lines: what is missing, and where to put it. Why the
                # exported file sitting on this same record does not count belongs
                # on the field's own help text, where it can be read once by
                # whoever wonders, rather than in a dialog every time.
                raise UserError(
                    _(
                        "%s has no proof of transfer yet.\n\n"
                        "Please attach the bank's confirmation in the Transfer "
                        "Result tab, then confirm again."
                    )
                    % rec.display_name
                )
        return True

    def action_confirm_epayment_success(self):
        """Ask for the note, then close the file.

        The press itself is one line of work — every payee is paid — so what it
        needs from the officer is the exception: which payee the bank could not
        credit and how they were settled instead. Asked for at the moment of the
        press rather than left as a field to remember, because that is the only
        moment anyone knows it.
        """
        self.ensure_one()
        self._check_result_recordable()
        self._check_transfer_proof()
        return {
            "name": _("Confirm Transfer Succeeded"),
            "type": "ir.actions.act_window",
            "res_model": "bank.payment.export.confirm",
            "view_mode": "form",
            "target": "new",
            "context": {"default_payment_export_id": self.id},
        }

    def _confirm_epayment_success(self, note=False):
        """Close the file: the money reached the payees.

        Every row is marked paid, including any the bank rejected. That is what the
        press asserts — not that the bank managed it, but that the payee has their
        money, settled outside the system where it had to be. ``note`` is where that
        is written down, and it is the only record of it: the office confirms the
        file as a whole and does not work row by row.
        """
        for rec in self:
            if rec.state == "paid":
                # A dialog left open and submitted twice would replace the note —
                # which is the only record of whatever the bank could not do — and
                # post it to the chatter a second time.
                raise UserError(_("%s is already closed.") % rec.display_name)
            rec._check_result_recordable()
            rec._check_transfer_proof()
            rejected = rec.export_line_ids.filtered(lambda line: line.state == "reject")
            payable = rec.export_line_ids - rejected
            payable._apply_epayment_result("success")
            # And the vouchers themselves: this press is ยืนยันจ่ายสำเร็จ for every
            # payee the file carries, so their own lifecycle has to say so. Already
            # paid ones are skipped rather than refused — a voucher settled by hand
            # before the file closed is not a reason the file cannot close.
            vouchers = payable.mapped("payment_id").filtered(
                lambda payment: payment.finance_state == "confirmed"
            )
            vouchers._mark_paid()
            # Nothing else would tell the accounting office about a voucher that
            # belongs to no request. The ones that do belong to one are handed over
            # by it, so they are filtered out where that is known.
            vouchers._hands_over_on_its_own()._handover_to_accounting()
            if note:
                rec.epayment_note = note
                rec.message_post(body=note, subject=_("Transfer Confirmed"))
            rec.state = "paid"
            # The base keeps a row's own rejection in a column that is a *related* on
            # this state, so writing it marks every row for recompute and wipes the
            # rejection — which would take the released payee's amount back into the
            # stored total and back onto the printed report. Re-asserted rather than
            # given a field of its own, which would be the honest fix and a wider
            # change than this belongs in.
            if rejected:
                rejected.write({"state": "reject"})
        return True

    # -------------------------------------------------------------------------
    def _domain_payment_id(self):
        """Select the KMITL transfer vouchers the finance office has confirmed for
        the bank (instead of posted Manual ones) when pulling every payment into an
        export batch. The accounting office has not booked them yet — their own
        status is still draft, which is why the base's ``state`` leaf is replaced
        rather than narrowed."""
        domain = super()._domain_payment_id()
        method_transfer_out = self._transfer_payment_method()
        new_domain = []
        for leaf in domain:
            if isinstance(leaf, (list, tuple)) and leaf[0] == "state":
                new_domain.append(("finance_state", "=", "confirmed"))
            elif (
                isinstance(leaf, (list, tuple))
                and leaf[0] == "payment_method_id"
                and method_transfer_out
            ):
                new_domain.append(("payment_method_id", "=", method_transfer_out.id))
            else:
                new_domain.append(leaf)
        # One file debits one account. Narrowing here is what keeps two paying
        # accounts out of the same batch in the first place, rather than only
        # rejecting the mix afterwards.
        if len(self) == 1 and self.paying_account_id:
            new_domain.append(
                ("payment_method_line_id", "=", self.paying_account_id.id)
            )
        return new_domain

    @api.model
    def action_create_bank_payment_export(self):
        """Open the create wizard when the selection has anything to decide.

        One paying account with no draft file of its own leaves nothing to ask, so
        that goes straight to the base's blank form. Anything else does: a selection
        spanning several หัวจ่าย becomes one file each (CONTEXT.md, ไฟล์ e-Payment),
        and where a draft file already debits an account the officer has to say
        whether these vouchers join it or start another — two files differing only
        by effective date is a normal way to hold an urgent batch apart from the
        month's run, and nothing but a person knows which this is.
        """
        payments = self.env["account.payment"].browse(
            self.env.context.get("active_ids", [])
        )
        if not payments:
            return
        self._check_constraint_create_bank_payment_export_groups(payments)
        groups = payments.grouped_by_paying_account()
        drafts = self.search(
            [
                ("state", "=", "draft"),
                ("paying_account_id", "in", [account.id for account in groups]),
            ]
        )
        if len(groups) == 1 and not drafts:
            return super().action_create_bank_payment_export()
        wizard = self.env["bank.payment.export.create"].create(
            {
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "paying_account_id": paying_account.id,
                            "payment_ids": [(6, 0, group.ids)],
                            "destination": "new",
                        },
                    )
                    for paying_account, group in groups.items()
                ]
            }
        )
        return {
            "name": _("Create e-Payment File"),
            "type": "ir.actions.act_window",
            "res_model": "bank.payment.export.create",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def _check_constraint_create_bank_payment_export_groups(self, payments):
        """Run the create-time checks per paying account.

        ``_check_constraint_create_bank_payment_export`` speaks for one file, and
        one of the things it insists on is a single paying account. A selection
        that spans four of them is four files, so it is checked four times rather
        than rejected once.
        """
        for group in payments.grouped_by_paying_account().values():
            self._check_constraint_create_bank_payment_export(group)
        return True

    def _get_context_create_bank_payment_export(self, payments):
        """Take the file's bank and paying account from the payments.

        The base derives the bank from the payment journal's bank account, which
        is empty at KMITL — a journal is a voucher type (ใบสำคัญ) and holds no
        bank. The paying account is where that lives now.
        """
        ctx = super()._get_context_create_bank_payment_export(payments)
        paying_accounts = payments.mapped("payment_method_line_id")
        if len(paying_accounts) == 1:
            ctx["default_paying_account_id"] = paying_accounts.id
            if paying_accounts.bank_id.bic:
                ctx["default_bank"] = paying_accounts.bank_id.bic
        return ctx
