# -*- coding: utf-8 -*-
from odoo import api, models

# Report used by every bank payment export text file (defined in the base
# module l10n_th_bank_payment_export).
BANK_PAYMENT_EXPORT_REPORT = (
    "l10n_th_bank_payment_export.bank_payment_export_text_file"
)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _render_qweb_text(self, report_ref, docids, data=None):
        """Re-encode the bank payment export text file to the encoding
        configured on the selected ``bank.export.format``.

        The core renderer always returns UTF-8 bytes, but Thai banks require
        the file to be encoded in TIS-620/cp874. Because every character used
        by the layouts is single-byte in cp874, the character-based padding
        done by ``bank.export.format.line`` stays byte-correct after the
        re-encode.
        """
        content, report_type = super()._render_qweb_text(
            report_ref, docids, data=data
        )
        report = self._get_report(report_ref)
        if report.report_name != BANK_PAYMENT_EXPORT_REPORT or not content:
            return content, report_type

        export = self.env["bank.payment.export"].browse(docids)[:1]
        encoding = export.bank_export_format_id.encoding or "utf-8"
        if encoding.lower().replace("-", "") in ("utf8", "utf"):
            return content, report_type

        text = content.decode("utf-8") if isinstance(content, bytes) else content
        return text.encode(encoding, errors="replace"), report_type
