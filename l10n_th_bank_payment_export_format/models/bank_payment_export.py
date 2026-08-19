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
