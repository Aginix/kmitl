import base64
import logging

from datetime import datetime
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class BankPaymentExport(models.Model):
    _inherit = "bank.payment.export"

    bank_export_format_id = fields.Many2one(
        comodel_name="bank.export.format",
        string="Bank Export Format",
        readonly=True,
        states={"draft": [("readonly", False)]},
        domain="[('bank', '=', bank)]",
        tracking=True,
    )
    export_file_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Exported File",
        readonly=True,
        copy=False,
        help="The very bytes that were handed to the bank. Kept because the file "
        "cannot be reproduced: the layouts read today's date, and some banks "
        "prepend a checksum over the body, so rendering the same record twice is "
        "not guaranteed to give the same file.",
    )

    @api.onchange("bank")
    def _onchange_bank_export_format_id(self):
        """Keep the layout on the bank the file is actually going to.

        The field carries a domain and nothing else, and a domain filters the
        dropdown without ever looking at the value already sitting in it. So
        changing the bank -- by hand, or by picking a template that carries a
        different one -- used to leave the previous bank's layout in place, and
        the file went out written in it.

        A bank with exactly one layout selects it, which is every bank but KTB:
        KTB ships two products (iPay and Direct Credit H/D/T) and which one the
        institute bought is not something this can decide, so it is left empty
        for the officer -- whose view already marks it required.

        Reached on the template path too, without listening for it: Odoo runs
        onchanges in passes, and a field a first-pass method changed is picked up
        by the next one (``models.py`` ``onchange``). ``_onchange_template_id``
        sets ``bank`` in pass one, so this runs in pass two.
        """
        for rec in self:
            if rec.bank_export_format_id.bank != rec.bank:
                rec.bank_export_format_id = False
            if rec.bank and not rec.bank_export_format_id:
                formats = self.env["bank.export.format"].search(
                    [("bank", "=", rec.bank)]
                )
                if len(formats) == 1:
                    rec.bank_export_format_id = formats

    @api.constrains("bank", "bank_export_format_id")
    def _check_bank_export_format_id(self):
        """The onchange above only guards the form.

        An export assembled in code -- from a payment selection, or by a test --
        never runs it, and a layout belonging to another bank would produce a
        file the receiving bank cannot read. Cheap to state, expensive to miss.
        """
        for rec in self:
            if rec.bank_export_format_id and rec.bank_export_format_id.bank != rec.bank:
                raise UserError(
                    _(
                        "Bank export format '%(format)s' belongs to another bank, "
                        "so it cannot be used on this file."
                    )
                    % {"format": rec.bank_export_format_id.display_name}
                )

    def _set_global_dict(self):
        """Set global dict for eval"""
        today = fields.Date.context_today(self)
        today_datetime = fields.Datetime.context_timestamp(
            self.env.user, datetime.now()
        )
        globals_dict = {
            "rec": self,
            "line": self.export_line_ids,
            "today": today,
            "today_datetime": today_datetime,
            "wht_cert": False,
            "invoices": self.env["account.move"],
        }
        return globals_dict

    def _update_global_dict(self, globals_dict, **kwargs):
        """Update global dict with kwargs"""
        globals_dict.update(kwargs)
        return globals_dict

    def _generate_bank_payment_text(self):
        self.ensure_one()
        globals_dict = self._set_global_dict()
        text_parts = []
        processed_match = set()

        # Get format from bank
        if not self.bank_export_format_id:
            raise UserError(_("Bank format not found."))

        exp_format_lines = self.bank_export_format_id.export_format_ids

        for idx, exp_format in enumerate(exp_format_lines):
            if exp_format.display_type:
                continue

            # Skip if value has already been processed, and need_loop is True
            if exp_format.need_loop and exp_format.match_group in processed_match:
                continue

            # Add idx to globals_dict
            globals_dict = self._update_global_dict(globals_dict, idx=idx)

            # Skip this line if condition is not met
            if not exp_format.need_loop and exp_format.condition_line:
                condition = safe_eval(
                    exp_format.condition_line, globals_dict=globals_dict
                )
                if not condition:
                    continue

            # Add value to the set of processed values
            if exp_format.match_group:
                processed_match.add(exp_format.match_group)

            if exp_format.need_loop:
                self._process_loop(
                    exp_format, exp_format_lines, globals_dict, text_parts
                )
                continue

            # Get value from instruction
            text_line = exp_format._get_value(globals_dict)
            text_parts.append(text_line)

            if exp_format.end_line:
                # TODO: Change this to configurable
                text_parts.append("\r\n")

        text = "".join(text_parts)
        return text

    def _process_loop(self, exp_format, exp_format_lines, globals_dict, text_parts):
        # Get all lines that match the current group
        wht_cert = False
        for idx_line, line in enumerate(self.export_line_ids):
            # Change the value of the line in the globals_dict
            payment = line.payment_id
            if hasattr(payment, "wht_cert_ids"):
                wht_cert = payment.wht_cert_ids

            globals_dict_line = self._update_global_dict(
                globals_dict,
                line=line,
                idx_line=idx_line,
                wht_cert=wht_cert,
                invoices=payment.reconciled_bill_ids,
            )

            # search only lines that match the current group and condition
            # filter in loop because we need to check condition_line
            exp_format_line_group = exp_format_lines.filtered(
                lambda fmt_line: (
                    fmt_line.match_group == exp_format.match_group
                    and (
                        not fmt_line.condition_line
                        or safe_eval(
                            fmt_line.condition_line, globals_dict=globals_dict_line
                        )
                    )
                )
            )

            processed_subloop = set()

            for exp_format_line in exp_format_line_group:
                # Sub-loop logic
                if exp_format_line.sub_loop:
                    self._process_sub_loop(
                        exp_format_line,
                        exp_format_line_group,
                        globals_dict_line,
                        text_parts,
                        processed_subloop,
                    )
                    continue

                # Get value from instruction
                text_line = exp_format_line._get_value(globals_dict_line)
                text_parts.append(text_line)

                if exp_format_line.end_line:
                    # TODO: Change this to configurable
                    text_parts.append("\r\n")
        return text_parts

    def _process_sub_loop(
        self,
        exp_format_line,
        exp_format_line_group,
        globals_dict_line,
        text_parts,
        processed_subloop,
    ):
        if exp_format_line.sub_value_loop not in processed_subloop:
            processed_subloop.add(exp_format_line.sub_value_loop)

            exp_format_sub_line_group = exp_format_line_group.filtered(
                lambda fmt_line: (
                    fmt_line.sub_value_loop == exp_format_line.sub_value_loop
                )
            )
            sub_lines = safe_eval(
                exp_format_line.sub_value_loop, globals_dict=globals_dict_line
            )

            for idx_sub_line, sub_line in enumerate(sub_lines):
                for exp_format_sub_line in exp_format_sub_line_group:
                    # Update globals_dict for sub-loop
                    globals_dict_sub_line = self._update_global_dict(
                        globals_dict_line, sub_line=sub_line, idx_sub_line=idx_sub_line
                    )

                    # Get value from sub-instruction
                    sub_text_line = exp_format_sub_line._get_value(
                        globals_dict_sub_line
                    )
                    text_parts.append(sub_text_line)

                    if exp_format_sub_line.end_line:
                        # TODO: Change this to configurable
                        text_parts.append("\r\n")
        return text_parts

    def _export_bank_payment_text_file(self):
        self.ensure_one()
        if not self.bank:
            return "Demo Text File. You must config `Bank Export Format` First."
        text = self._generate_bank_payment_text()
        prefix = self._get_text_file_prefix(text)
        return "{}{}".format(prefix, text) if prefix else text

    def _check_constraint_line(self):
        """The money has to leave from an account at the bank the file goes to.

        Every layout writes the debit account into its own header, and the
        receiving bank reads it as one of its own. A file addressed to KTB that
        debits an SCB account asks KTB to debit an account it has never heard
        of, so KTB refuses the file -- and the refusal says nothing about which
        account, because as far as the bank is concerned the account simply is
        not there.

        Nothing checked this. The bank is derived from the paying account when a
        file is created from a payment selection, but an officer can change
        either side afterwards and the two then disagree in silence: the form
        says KTB, the header says an SCB account, and the first sign of trouble
        is a rejection from the bank.

        A line with no sending account at all is the same fault seen earlier:
        the header renders the field as zeros.
        """
        res = super()._check_constraint_line()
        self.ensure_one()
        if not self.bank:
            return res
        wrong = self.export_line_ids.filtered(
            lambda line: line.sending_bank_id.bic != self.bank
        )
        if wrong:
            bank = dict(self._fields["bank"]._description_selection(self.env)).get(
                self.bank, self.bank
            )
            raise UserError(
                _(
                    "This file goes to %(bank)s, so every payment on it has to be "
                    "paid out of an account at %(bank)s. These are not:\n%(lines)s"
                )
                % {
                    "bank": bank,
                    "lines": "\n".join(
                        "- %s: %s"
                        % (
                            line.payment_id.display_name,
                            line.sending_bank_id.display_name
                            or _("no bank account on the journal"),
                        )
                        for line in wrong
                    ),
                }
            )
        return res

    def _check_receiving_bank_code(self, lines):
        """Refuse a file whose payees' banks have no clearing code.

        The layouts that cross banks -- SCB's 003 record, KTB's -- write the
        receiving bank as a three-digit clearing code read off ``res.bank``.
        It is seeded, but under ``noupdate``, so a database that had the bank
        records before the codes were added still has them empty; the field
        then goes out as three spaces and the bank refuses the file without
        saying which field it could not read.

        Called by the banks whose layout actually writes it: KBANK and BAY
        credit their own accounts only and carry no such field, so requiring
        one there would block a file that is perfectly good.
        """
        self.ensure_one()
        missing = lines.filtered(
            lambda line: not line.payment_partner_bank_id.bank_id.bank_code
        )
        if missing:
            raise UserError(
                _(
                    "The file names each payee's bank by its clearing code, and "
                    "these banks have none. Fill in the Bank Code in "
                    "Settings > Banks:\n%s"
                )
                % "\n".join(
                    sorted(
                        {
                            "- %s (%s)"
                            % (
                                line.payment_partner_bank_id.bank_id.display_name
                                or line.payment_id.display_name,
                                line.payment_id.display_name,
                            )
                            for line in missing
                        }
                    )
                )
            )
        return True

    def _check_bank_specific_constraint(self, payments):
        """Hook for the rules a particular bank puts on a batch of payments.

        Kept apart from ``_check_constraint_create_bank_payment_export`` so that
        a localisation replacing that method outright — one whose payments are
        exported before posting, say, which the base check rejects — can still
        invoke the per-bank rules layered on top instead of silencing them.
        """
        return True

    def _get_text_file_prefix(self, text):
        """Hook returning a prefix block that a CSV layout cannot express
        (e.g. a checksum line computed over the whole file body).

        Base implementation returns an empty string. Override per bank, e.g.
        SCB prepends a 40-character SHA-1 checksum line.
        """
        self.ensure_one()
        return ""

    # -------------------------------------------------------------------------
    # The exported file is kept, not just downloaded
    # -------------------------------------------------------------------------
    def action_get_all_payments(self):
        """Rebuild the file's rows from every payment that currently qualifies.

        The base releases the rows *after* searching, which empties the file: the
        domain matches ``export_status == 'draft'`` only, so the payments this file
        already holds are filtered out of the result, and the unlink that follows
        then drops them. Pressing the button a second time on a file of twenty rows
        with two fresh candidates left two rows behind and released the twenty
        without a word. Releasing first puts those twenty back at ``draft`` in time
        for the search to find them again.
        """
        self.ensure_one()
        self.export_line_ids.unlink()
        payments = self.env["account.payment"].search(self._domain_payment_id())
        if payments:
            self.env["bank.payment.export.line"].create(
                [
                    {"payment_export_id": self.id, "payment_id": payment.id}
                    for payment in payments
                ]
            )
        return True

    def _render_bank_payment_file(self):
        """Return the file's bytes, encoded as the chosen layout requires.

        Rendered through the report rather than by calling
        ``_export_bank_payment_text_file`` directly, so the cp874 re-encode in
        ``ir.actions.report._render_qweb_text`` stays the single place that knows
        which code page a bank wants.
        """
        self.ensure_one()
        content, _report_type = self.env["ir.actions.report"]._render_qweb_text(
            self._get_view_report_text(), self.ids
        )
        return content

    def _store_bank_payment_file(self):
        """Render the file once and keep it as an attachment on the record."""
        self.ensure_one()
        content = self._render_bank_payment_file()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "{}.txt".format(self._get_report_base_filename()),
                "datas": base64.b64encode(content),
                "mimetype": "text/plain",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        self.export_file_id = attachment
        return attachment

    def _action_download_export_file(self):
        """Hand the stored bytes over, and let the form catch up.

        Deliberately not ``target: 'self'``. The web client redirects for that and
        returns, never calling the button's ``onClose`` — so the record on screen
        keeps showing the state it had before the press, and the officer has to
        reload the page to see that the file went out. Every other target reaches
        the branch that does call it, which is what reloads the form. (The base
        module got this for free by returning a report action: the report
        downloader calls ``onClose`` itself.)

        The URL answers with ``Content-Disposition: attachment``, so the window the
        client opens downloads the file and closes rather than showing a page.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/{}?download=true".format(self.export_file_id.id),
            "target": "new",
        }

    def action_download_export_file(self):
        """Hand out the file that was exported, unchanged."""
        self.ensure_one()
        if not self.export_file_id:
            raise UserError(
                _(
                    "No file is kept for %s. It was exported before the file "
                    "started being stored, so it can only be produced again by "
                    "taking the record back to draft and exporting it afresh — "
                    "which will not give the same bytes."
                )
                % self.display_name
            )
        return self._action_download_export_file()

    def action_export_text_file(self):
        """Keep the file, then hand it over.

        The base prints the report and lets the browser own the only copy. What
        went to the bank has to stay somewhere the office can look at it again,
        and a failed download must not leave a record claiming it was exported
        with nothing to show.
        """
        self.ensure_one()
        self._store_bank_payment_file()
        self.action_done()
        return self._action_download_export_file()

    def action_draft(self):
        """Only a file that has not been exported may go back to draft.

        The base writes the state with no guard at all, so a call from outside the
        form could take an exported file back to ``draft`` while its payments stay
        at ``exported`` — the file would then say it was never sent and the
        vouchers that they were.
        """
        for record in self:
            if record.state != "confirm":
                raise UserError(
                    _(
                        "%s cannot be taken back to draft from its current state. "
                        "Only a confirmed file that has not been exported yet may "
                        "be reopened."
                    )
                    % record.display_name
                )
        return super().action_draft()
