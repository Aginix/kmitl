import logging

from datetime import datetime
from odoo import models, fields, _
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
                lambda l: (
                    l.match_group == exp_format.match_group
                    and (
                        not l.condition_line
                        or safe_eval(l.condition_line, globals_dict=globals_dict_line)
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
                lambda l: l.sub_value_loop == exp_format_line.sub_value_loop
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
