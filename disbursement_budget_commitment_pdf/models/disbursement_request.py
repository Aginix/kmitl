import base64
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

_REPORT_XMLID = "budget_commitment_pdf.action_report_budget_commitment"
_ATTACHMENT_MARKER = "disbursement_budget_commitment_pdf:auto"


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.budget_commitment_id:
                rec._sync_budget_commitment_pdf_attachment()
        return records

    def write(self, values):
        if "budget_commitment_id" in values:
            previous = {rec.id: rec.budget_commitment_id.id for rec in self}
            res = super().write(values)
            for rec in self:
                if previous.get(rec.id) != rec.budget_commitment_id.id:
                    rec._sync_budget_commitment_pdf_attachment()
            return res
        return super().write(values)

    def _sync_budget_commitment_pdf_attachment(self):
        """Replace the auto-attached commitment PDF on this DR with the current one.

        Removes any previously auto-attached PDF (identified by the marker in
        `description`), then, if a commitment is linked, renders its PDF and
        attaches it to this DR. User-uploaded attachments are untouched.
        """
        self.ensure_one()
        Attachment = self.env["ir.attachment"].sudo()
        Attachment.search([
            ("res_model", "=", "disbursement.request"),
            ("res_id", "=", self.id),
            ("description", "=", _ATTACHMENT_MARKER),
        ]).unlink()

        commitment = self.budget_commitment_id
        if not commitment:
            return

        report = self.env["ir.actions.report"].sudo()
        try:
            pdf, _dummy = report._render_qweb_pdf(_REPORT_XMLID, commitment.ids)
        except Exception:
            _logger.exception(
                "disbursement_budget_commitment_pdf: failed to render PDF "
                "for commitment %s on DR %s",
                commitment.name,
                self.name,
            )
            return

        fname = "Budget Commitment - %s.pdf" % (
            (commitment.name or str(commitment.id)).replace("/", "-")
        )
        Attachment.create({
            "name": fname,
            "type": "binary",
            "datas": base64.b64encode(pdf),
            "mimetype": "application/pdf",
            "res_model": "disbursement.request",
            "res_id": self.id,
            "description": _ATTACHMENT_MARKER,
        })
