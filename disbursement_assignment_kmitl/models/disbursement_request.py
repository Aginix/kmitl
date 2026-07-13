# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import str2bool

# The "To Do" activity raised on a request when an officer is assigned.
ASSIGN_ACTIVITY_XMLID = "mail.mail_activity_data_todo"

# ir.config_parameter that relaxes the self-claim guard. Defaults to True:
# because assignment is advisory, an officer may claim a mis-routed request
# out of the box. Set to False to lock claims to the assigned officer/manager.
TAKEOVER_PARAM = "disbursement.allow_takeover_assigned"

OFFICER_GROUP = "disbursement.group_disbursement_officer"
MANAGER_GROUP = "disbursement.group_disbursement_manager"


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    assigned_to = fields.Many2one(
        "res.users",
        string="Assigned Officer",
        copy=False,
        tracking=True,
        index=True,
    )
    # Not added to READONLY_STATES on purpose: it must stay writable at the
    # ``signed`` state, which is exactly where officers are assigned.
    assignment_can_assign_me = fields.Boolean(
        compute="_compute_assignment_can_assign_me",
    )
    # Set when verification returns a signed request to the creator for a fix.
    # Drives the resubmit path (draft -> signed, skipping a second head sign).
    returned_for_edit = fields.Boolean(
        string="Returned for Correction",
        copy=False,
    )

    # -- guards ----------------------------------------------------------
    def _assignment_takeover_allowed(self):
        return str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(TAKEOVER_PARAM, default=True)
        )

    def _assignment_is_manager(self):
        return self.env.user.has_group(MANAGER_GROUP)

    def _assignment_can_claim(self):
        """Whether the current user may self-assign this single request."""
        self.ensure_one()
        if not self.assigned_to:
            return True
        if self.assigned_to == self.env.user:
            return False
        return self._assignment_is_manager() or self._assignment_takeover_allowed()

    @api.depends("assigned_to")
    def _compute_assignment_can_assign_me(self):
        for rec in self:
            rec.assignment_can_assign_me = rec._assignment_can_claim()

    # -- activity bookkeeping --------------------------------------------
    def _assignment_activity_summary(self):
        return _("Assigned as responsible verification officer")

    def _assignment_notify(self, user):
        self.ensure_one()
        self.activity_schedule(
            ASSIGN_ACTIVITY_XMLID,
            user_id=user.id,
            summary=self._assignment_activity_summary(),
        )

    def _assignment_clear_activity(self, user):
        """Drop the open assignment to-do previously raised for ``user``."""
        self.ensure_one()
        activity_type = self.env.ref(ASSIGN_ACTIVITY_XMLID)
        summary = self._assignment_activity_summary()
        stale = self.activity_ids.filtered(
            lambda a: a.user_id == user
            and a.activity_type_id == activity_type
            and a.summary == summary
        )
        stale.unlink()

    def _assignment_close_activity(self):
        """Close the open assignment to-do(s) once the verification stage ends.

        Called when a request is validated, reset, or cancelled. Uses sudo so
        the to-do is cleared regardless of who performs the action (assignment
        is not locked, so a request may be validated by another officer).
        """
        activity_type = self.env.ref(ASSIGN_ACTIVITY_XMLID)
        summary = self._assignment_activity_summary()
        for rec in self:
            stale = rec.sudo().activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type
                and a.summary == summary
            )
            stale.unlink()

    # -- button actions --------------------------------------------------
    def action_assignment_assign_me(self):
        me = self.env.user
        for rec in self:
            if rec.assigned_to == me:
                continue
            if not rec._assignment_can_claim():
                raise UserError(
                    _("This document is already assigned to %s.")
                    % rec.assigned_to.display_name
                )
            if rec.assigned_to:
                rec._assignment_clear_activity(rec.assigned_to)
            rec.assigned_to = me
        return True

    def action_assignment_unassign(self):
        if not self._assignment_is_manager():
            raise AccessError(_("Only a manager can unassign the officer."))
        for rec in self:
            if rec.assigned_to:
                rec._assignment_clear_activity(rec.assigned_to)
            rec.assigned_to = False
        return True

    def action_assignment_open_wizard(self):
        self.ensure_one()
        if not self._assignment_is_manager():
            raise AccessError(_("Only a manager can assign another officer."))
        return {
            "name": _("Assign Officer"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.assign.officer.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

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
        creator. The responsible officer is kept, so once the creator resubmits
        it goes straight back to verification (see ``action_resubmit_verification``)
        without a second head sign.
        """
        self.ensure_one()
        if self.state != "signed":
            raise UserError(
                _("Only a request under verification (signed) can be returned.")
            )
        self.returned_for_edit = True
        # signed -> draft; the assignment override also closes the officer's
        # verification to-do.
        self.action_draft()
        self.message_post(
            body=_("Returned for correction: %s") % reason,
        )
        if self.user_id:
            self.activity_schedule(
                ASSIGN_ACTIVITY_XMLID,
                user_id=self.user_id.id,
                summary=_("Returned for correction"),
                note=reason,
            )

    def action_resubmit_verification(self):
        """Creator resubmits a corrected request straight back to verification.

        Skips the head sign (already done before the return) and re-notifies
        the responsible officer.
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
        self._assignment_auto_assign()
        self.message_post(body=_("Corrected and returned to verification."))

    # -- auto-assign + workflow hooks ------------------------------------
    def _assignment_auto_assign(self):
        """Assign the matching officer to signed requests and raise a To-Do.

        Requests that already carry a responsible officer (manual override or
        a previous sign) keep their officer -- the rules never overwrite them.
        The rule search is sudo'd so the automatic Sarabun sign path (run by a
        head who may not read rules) still routes correctly.
        """
        Rule = self.env["disbursement.assignment.rule"].sudo()
        for rec in self.filtered(lambda r: r.state == "signed"):
            if not rec.assigned_to:
                rule = Rule._find_for_request(rec)
                if not rule:
                    continue
                rec.assigned_to = rule.user_id
            if rec.assigned_to != self.env.user:
                rec._assignment_clear_activity(rec.assigned_to)
                rec._assignment_notify(rec.assigned_to)

    def action_sign(self):
        res = super().action_sign()
        self._assignment_auto_assign()
        return res

    def action_validate(self):
        res = super().action_validate()
        self._assignment_close_activity()
        return res

    def action_draft(self):
        res = super().action_draft()
        self._assignment_close_activity()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self._assignment_close_activity()
        return res
