from odoo import _, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        ondelete="set null",
        index=True,
        copy=False,
        tracking=True,
    )

    reference = fields.Reference(
        selection_add=[('approval.request', 'Approval Request')],
        ondelete={'approval.request': 'set null'},
    )

    returned_to_approval = fields.Boolean(
        string="Returned to Approval Request",
        copy=False,
        help="Set when this request was returned: it is kept as-is at 'signed' "
             "and its approval request is bounced to 'returned' for correction. "
             "Cleared once the correction is confirmed.",
    )

    def action_validate(self):
        """Block validation while a correction is pending on the approval side.

        The request is kept at 'signed' when returned, so without this guard the
        officer could validate/approve (and obligate budget) against the stale
        data before the requester confirms the correction."""
        for record in self:
            if record.returned_to_approval:
                raise UserError(
                    _(
                        "This request was returned to its approval request. "
                        "Please wait for the corrected approval to be confirmed "
                        "before validating."
                    )
                )
        return super().action_validate()

    def _action_return_for_edit(self, reason):
        """Return an approval-linked request to its approval request instead of
        to draft.

        For a request created from an approval request, returning it keeps the
        DR as-is at 'signed' (no cancel, no budget change) and bounces the
        approval request to 'returned' so the requester can correct a limited
        set of fields in place. Requests with no approval request keep the
        standard signed -> draft return-for-correction behaviour."""
        ar_linked = self.filtered("approval_request_id")
        for record in ar_linked:
            record._return_to_approval_request(reason)
        remaining = self - ar_linked
        if remaining:
            return super(
                DisbursementRequest, remaining
            )._action_return_for_edit(reason)
        return True

    def _return_to_approval_request(self, reason):
        """Bounce the linked approval request without touching this DR.

        The DR is kept as-is at 'signed' (no cancel, no budget change); only the
        approval request moves to 'returned' for correction. A banner is shown
        on the DR and a To-Do is raised for the approval request's owner."""
        self.ensure_one()
        if self.state != "signed":
            raise UserError(
                _("Only a request under verification (signed) can be returned.")
            )
        self.returned_to_approval = True
        approval = self.approval_request_id
        approval.action_return()
        self.message_post(body=_("Returned to approval request: %s") % reason)
        approval.message_post(
            body=_(
                "Disbursement %(dr)s was returned for correction: %(reason)s",
                dr=self.name,
                reason=reason,
            )
        )
        # Raise a To-Do on this DR for the approval request's owner, reminding
        # them to correct and confirm the approval request.
        responsible = approval.user_id or approval.create_uid
        if responsible:
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=responsible.id,
                summary=_("Correct and confirm approval request"),
                note=reason,
            )
        return True

    def _apply_approval_correction(self, approval):
        """Push a returned approval request's corrected payee bank, description
        and disbursement evidence onto this request, then clear the returned
        banner. The DR is kept at 'signed' for the officer to continue
        verification."""
        self.ensure_one()
        self.note = approval.description
        payee_bank = {
            payee.partner_id.id: payee.partner_bank_id.id
            for payee in approval.payee_ids
            if payee.partner_bank_id
        }
        for line in self.line_ids:
            bank = payee_bank.get(line.partner_id.id)
            if bank:
                line.partner_bank_id = bank
        approval._copy_new_evidence_to_disbursement(self)
        self.returned_to_approval = False
        self.message_post(
            body=_(
                "Approval correction applied: payee bank, description and "
                "evidence updated. Please continue verification."
            )
        )
        return True

    def action_view_approval_request(self):
        self.ensure_one()
        if not self.approval_request_id:
            raise UserError(
                _("No Approval Request linked to this request.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Approval Request"),
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
