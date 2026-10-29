import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    is_disbursement_evidence = fields.Boolean(
        string="Disbursement Evidence",
        default=False,
    )

    def check(self, mode, values=None):
        """The requester's evidence stays on the approval request but is shown
        on every ใบขอเบิก of it (ADR-0009): whoever may read such a ใบขอเบิก may
        read the file, even without access to the request itself."""
        records = self
        # Skip under sudo: base check() already allows it, and the sudo read in
        # _disbursement_readable_evidence re-enters check() through _read.
        if mode == "read" and self and not self.env.su and self.env.user._is_internal():
            records -= self._disbursement_readable_evidence()
        return super(IrAttachment, records).check(mode, values=values)

    def _disbursement_readable_evidence(self):
        """Approval-request evidence among these attachments that the current
        user reaches through a ใบขอเบิก they can read."""
        evidence = self.sudo().filtered(
            lambda a: a.res_model == "approval.request" and a.is_disbursement_evidence
        )
        DR = self.env["disbursement.request"]
        if not evidence or not DR.check_access_rights("read", raise_exception=False):
            return self.browse()
        # Searched as the user, so record rules keep only the readable ones.
        requests = (
            DR.search([("approval_request_id", "in", evidence.mapped("res_id"))])
            .sudo()
            .approval_request_id
        )
        return self.browse((evidence & requests.disbursement_attachment_ids).ids)
