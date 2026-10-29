# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError

# Generic "To Do" activity raised on the creator when a request in the circuit
# is sent back for correction (back to draft).
RETURN_ACTIVITY_XMLID = "mail.mail_activity_data_todo"


class DisbursementRequest(models.Model):
    """Send-back workflow on the DR.

    A request in the circuit goes back to ``draft`` for its maker to fix and
    resubmit (``action_resubmit_verification``). It is independent of who (if
    anyone) is the responsible officer -- the ``disbursement_validation_assignment``
    addon layers officer assignment on top and overrides
    ``_verification_officer`` so the To-Dos reach the assigned officer instead
    of the creator.
    """

    _inherit = "disbursement.request"

    # Set when a station sends the request back to its maker for a fix. Drives
    # the resubmit path (draft -> back into the circuit, skipping a second head
    # sign).
    returned_for_edit = fields.Boolean(
        string="Returned for Correction",
        copy=False,
    )
    def _verification_officer(self):
        """The user responsible for verifying this request, used as the target
        of the return To-Dos. Defaults to the creator; the assignment addon
        overrides this to prefer the assigned officer."""
        self.ensure_one()
        return self.user_id

    # -- return for correction -------------------------------------------
    def action_return_open_wizard(self):
        """Open the wizard that collects the mandatory return reason."""
        self.ensure_one()
        return {
            "name": _("Return for Correction"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.return.request.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _action_return_for_edit(self, reason):
        """Send a request in the circuit back to the creator for correction.

        The request returns to ``draft`` so the creator can edit it, the reason
        goes on the chatter, and the creator gets a To-Do. Once the creator
        resubmits it re-enters the circuit at its first station (see
        ``action_resubmit_verification``) without a second head sign.
        """
        self.ensure_one()
        if self.state not in ("signed", "in_progress"):
            raise UserError(_("Only a request in the circuit can be sent back."))
        self._disbursement_check_send_back()
        self.returned_for_edit = True
        self.with_context(
            work_center_departure="send_back", work_center_reason=reason
        ).action_draft()
        self.message_post(
            body=Markup(
                _(
                    "<p><b>Sent back for correction</b></p>"
                    "<p>Returned to the requester and reset to draft so it can be "
                    "corrected and resubmitted.<br/>Reason: <b>%s</b></p>"
                )
            )
            % reason,
            subtype_xmlid="mail.mt_comment",
        )
        if self.user_id:
            self.activity_schedule(
                RETURN_ACTIVITY_XMLID,
                user_id=self.user_id.id,
                summary=_("Sent back for correction"),
                note=reason,
            )

    def action_resubmit_verification(self):
        """Creator resubmits a corrected request straight back into the circuit.

        Skips the head sign (already done before the send-back); the request
        re-enters at its first station.
        """
        self.ensure_one()
        if not (self.state == "draft" and self.returned_for_edit):
            raise UserError(
                _("Only a returned request in draft can be resubmitted.")
            )
        if not self.line_ids:
            raise UserError(
                _("Cannot resubmit a disbursement request with no lines.")
            )
        self.returned_for_edit = False
        self.state = "signed"
        self.message_post(body=_("Corrected and sent back into the circuit."))
        self.with_context(disbursement_resubmit=True)._on_signed()
