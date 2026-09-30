import io

from odoo import models
from odoo.modules.module import get_module_resource
from odoo.tools.pdf import merge_pdf

CONTRACT_REPORT = "advance_payment_contract_pdf.report_advance_payment_contract"


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        """Append the static รายการส่งใช้เงินยืม page after page 1 of every
        printed loan contract. Done at stream level so every render path
        (button, attachment, e-Saraban) gets it."""
        streams = super()._render_qweb_pdf_prepare_streams(
            report_ref, data, res_ids=res_ids
        )
        if self._get_report(report_ref).report_name != CONTRACT_REPORT:
            return streams
        path = get_module_resource(
            "advance_payment_contract_pdf",
            "static",
            "pdf",
            "advance_payment_contract_page2.pdf",
        )
        with open(path, "rb") as f:
            page2 = f.read()
        for stream_data in streams.values():
            stream = stream_data.get("stream")
            if stream:
                stream_data["stream"] = io.BytesIO(
                    merge_pdf([stream.getvalue(), page2])
                )
                stream.close()
        return streams
