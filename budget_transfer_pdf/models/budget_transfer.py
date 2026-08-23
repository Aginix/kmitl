import base64
import logging

from odoo import models

_logger = logging.getLogger(__name__)

_REPORT_XMLID = "budget_transfer_pdf.action_report_budget_transfer"


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    def _post_transfer(self):
        super()._post_transfer()
        self._attach_posted_pdf()

    def _attach_posted_pdf(self):
        """Render the transfer PDF and store it as an ir.attachment on the record."""
        report = self.env["ir.actions.report"].sudo()
        for transfer in self:
            try:
                pdf, _dummy = report._render_qweb_pdf(_REPORT_XMLID, transfer.ids)
            except Exception:
                _logger.exception(
                    "budget_transfer_pdf: failed to render PDF for transfer %s",
                    transfer.name,
                )
                continue
            fname = "%s.pdf" % (transfer.name or "budget-transfer").replace("/", "-")
            self.env["ir.attachment"].sudo().create(
                {
                    "name": fname,
                    "type": "binary",
                    "datas": base64.b64encode(pdf),
                    "mimetype": "application/pdf",
                    "res_model": "budget.transfer",
                    "res_id": transfer.id,
                }
            )
