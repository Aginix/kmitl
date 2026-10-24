# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError

# Generic "To Do" activity raised on the creator when a signed request is
# returned for correction (signed -> draft).
RETURN_ACTIVITY_XMLID = "mail.mail_activity_data_todo"

# The "please re-verify" To-Do raised when an approver/accounting returns a
# request to the verification officer (see _action_return_to_verification).
_ACT_REVERIFY_XMLID = "disbursement.mail_activity_dr_reverify"


class DisbursementRequest(models.Model):
    """Return / re-verification workflow on the DR.

    Three flows live here, all independent of who (if anyone) is the responsible
    verification officer -- the ``disbursement_assignment_kmitl`` addon layers
    officer assignment on top and overrides ``_verification_officer`` so the
    To-Dos below reach the assigned officer instead of the creator:

    * return-for-correction: a signed request goes back to ``draft`` for the
      creator to fix and resubmit (``action_resubmit_verification``);
    * return-to-verification: a verified/approved request goes back to
      ``signed`` for the officer to re-check;
    * return-from-head: a submitted request goes back to ``draft`` before the
      head has signed it.

    ``_return_step_handler`` maps the wizard's mode onto these, and is where
    add-ons contribute the steps of their own phase.
    """

    _inherit = "disbursement.request"

    # Set when verification returns a signed request to the creator for a fix.
    # Drives the resubmit path (draft -> signed, skipping a second head sign).
    returned_for_edit = fields.Boolean(
        string="Returned for Correction",
        copy=False,
    )
    # Set when an approver (verified) or the accounting room (approved) returns
    # the request to the verification officer for a re-check. The request goes
    # back to 'signed'; cleared once the officer re-validates it.
    returned_to_verification = fields.Boolean(
        string="Returned to Verification",
        copy=False,
        tracking=True,
    )
    return_verification_reason = fields.Text(
        string="Return to Verification Reason",
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
        """Send a signed request back to the creator for correction.

        Verification returns the request to ``draft`` so the creator can edit
        it, records the reason on the chatter, and raises a To-Do for the
        creator. Once the creator resubmits it goes straight back to
        verification (see ``action_resubmit_verification``) without a second
        head sign.
        """
        self.ensure_one()
        if self.state != "signed":
            raise UserError(
                _("Only a request under verification (signed) can be returned.")
            )
        self.returned_for_edit = True
        self.action_draft()
        self.message_post(
            body=_(
                "<p><b>Returned for correction</b></p>"
                "<p>Returned to the requester and reset to draft so it can be "
                "corrected and resubmitted.<br/>Reason: <b>%s</b></p>"
            ) % reason,
            subtype_xmlid="mail.mt_comment",
        )
        if self.user_id:
            self.activity_schedule(
                RETURN_ACTIVITY_XMLID,
                user_id=self.user_id.id,
                summary=_("Returned for correction"),
                note=reason,
            )

    def action_resubmit_verification(self):
        """Creator resubmits a corrected request straight back to verification.

        Skips the head sign (already done before the return).
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
        self.message_post(body=_("Corrected and returned to verification."))

    # -- return from the head (submitted -> draft) -----------------------
    def _return_step_handler(self, mode):
        """The method the return wizard runs for ``mode``, or None if unknown.

        A table on the model rather than an if/else in the wizard, so an add-on
        can contribute its own steps by extending it instead of overriding the
        wizard."""
        return {
            "edit": self._action_return_for_edit,
            "verification": self._action_return_to_verification,
            "head": self._action_return_from_head,
        }.get(mode)

    def _return_wizard_action(self, name, mode):
        """The act_window opening the reason wizard for the ``mode`` step."""
        self.ensure_one()
        return {
            "name": name,
            "type": "ir.actions.act_window",
            "res_model": "disbursement.return.request.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id, "default_mode": mode},
        }

    def action_return_head_open_wizard(self):
        """Open the reason wizard for the head returning a submitted request to
        the requester."""
        return self._return_wizard_action(_("Return to Requester"), "head")

    def _action_return_from_head(self, reason):
        """Send a submitted request back to the requester before it is signed.

        Unlike ``_action_return_for_edit`` this leaves ``returned_for_edit``
        unset: the head has not signed yet, so the requester resubmits through
        the normal Submit and the head signs the corrected request."""
        self.ensure_one()
        if self.state != "submitted":
            raise UserError(
                _("Only a submitted request can be returned to the requester.")
            )
        self.action_draft()
        self.message_post(
            body=_(
                "<p><b>Returned to the requester</b></p>"
                "<p>Returned by the head and reset to draft so it can be "
                "corrected and submitted again.<br/>Reason: <b>%s</b></p>"
            ) % reason,
            subtype_xmlid="mail.mt_comment",
        )
        if self.user_id:
            self.activity_schedule(
                RETURN_ACTIVITY_XMLID,
                user_id=self.user_id.id,
                summary=_("Returned by the head"),
                note=reason,
            )

    # -- return to verification (approver / accounting -> officer) -------
    def action_return_verification_open_wizard(self):
        """Open the reason wizard for returning the request to the verification
        officer (used by the approver at 'verified' and accounting at 'approved')."""
        self.ensure_one()
        return {
            "name": _("Return to Verification"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.return.request.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_id": self.id,
                "default_mode": "verification",
            },
        }

    def _action_return_to_verification(self, reason):
        """Send a verified/approved request back to the verification officer.

        Moves the request to 'signed' (where the officer re-verifies), records
        the reason, and raises the officer's To-Do. The budget is left
        untouched: an approved request keeps its obligation/consumption, and a
        re-approval will not double-cut it (see _action_approve_budget)."""
        self.ensure_one()
        if self.state not in ("verified", "approved"):
            raise UserError(
                _("Only a verified or approved request can be returned to "
                  "verification.")
            )
        self.returned_to_verification = True
        self.return_verification_reason = reason
        self.state = "signed"
        # Reset the verification stamp and the two-approver sub-workflow so
        # re-validation starts a clean cycle (budget stays intact; re-approval is
        # idempotent). Both archive their signature rows.
        self._reset_verification()
        self._reset_approval()
        # Always raise a "please re-verify" To-Do so the responsible user is
        # aware of the re-check.
        recipient = self._verification_officer()
        if recipient:
            self.activity_schedule(
                _ACT_REVERIFY_XMLID,
                user_id=recipient.id,
                note=reason or "",
            )
        self.message_post(
            body=_(
                "<p><b>Returned to verification</b></p>"
                "<p>Returned to the verification officer for re-checking."
                "<br/>Reason: <b>%s</b></p>"
            ) % reason,
            subtype_xmlid="mail.mt_comment",
        )
        return True

    def _clear_returned_to_verification(self):
        act_type = self.env.ref(_ACT_REVERIFY_XMLID, raise_if_not_found=False)
        for rec in self:
            if not rec.returned_to_verification:
                continue
            rec.returned_to_verification = False
            rec.return_verification_reason = False
            if act_type:
                rec.activity_ids.filtered(
                    lambda a: a.activity_type_id == act_type
                ).unlink()

    # -- workflow hooks --------------------------------------------------
    def action_validate(self):
        res = super().action_validate()
        self._clear_returned_to_verification()
        return res

    def action_draft(self):
        res = super().action_draft()
        self._clear_returned_to_verification()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self._clear_returned_to_verification()
        return res
