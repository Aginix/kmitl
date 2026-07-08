# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError

# ir.config_parameter that relaxes the self-claim guard. Defaults to True:
# because assignment is advisory, an officer may claim a mis-routed request
# out of the box. Set to False to lock claims to the assigned officer/manager.
TAKEOVER_PARAM = "disbursement.allow_takeover_assigned"

# Kept for tests / external code that still imports this. The activity type
# itself lives in ``base_assignment``; the constant is a re-export.
ASSIGN_ACTIVITY_XMLID = "base_assignment.mail_activity_assignment"


class DisbursementRequest(models.Model):
    _name = "disbursement.request"
    _inherit = ["disbursement.request", "assignment.mixin"]

    _assign_user_group = "disbursement.group_disbursement_officer"
    _assign_manager_group = "disbursement.group_disbursement_manager"

    assigned_to = fields.Many2one(
        "res.users",
        string="Assigned Officer",
        copy=False,
        tracking=True,
        index=True,
    )
    # Set when verification returns a signed request to the creator for a fix.
    # Drives the resubmit path (draft -> signed, skipping a second head sign).
    returned_for_edit = fields.Boolean(
        string="Returned for Correction",
        copy=False,
    )

    # -- assignment mixin hooks ------------------------------------------
    def _assignment_activity_summary(self):
        return _("Assigned as responsible verification officer")

    def _assignment_takeover_param(self):
        return TAKEOVER_PARAM

    def _assignment_takeover_default(self):
        # Advisory model: an officer may grab a mis-routed request out of the
        # box (procurement defaults False; disbursement defaults True).
        return True

    # -- bulk-close activities on state exit -----------------------------
    # base's ``_assignment_clear_activity`` is per-user; verification-stage
    # transitions (validate / reset / cancel) need to close every open
    # assignment To-Do on the record regardless of who scheduled it, so a
    # different officer completing verification also clears the original
    # assignee's inbox.
    def _assignment_close_activity(self):
        activity_type = self.env.ref(self._assignment_activity_xmlid())
        summary = self._assignment_activity_summary()
        for rec in self:
            stale = rec.sudo().activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type
                and a.summary == summary
            )
            stale.unlink()

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
        it goes straight back to verification (see
        ``action_resubmit_verification``) without a second head sign.
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
                self._assignment_activity_xmlid(),
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
