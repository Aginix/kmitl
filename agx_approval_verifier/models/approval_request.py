from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

VERIFY_TODO = "agx_approval_verifier.mail_activity_verify_request"
RETURNED_TODO = "agx_approval_verifier.mail_activity_request_returned"


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # ผู้ตรวจสอบ: the one Request Verifier named on this request, who
    # gets its to_verify Todo. Any member of the Verifier group may still act.
    verifier_id = fields.Many2one(
        comodel_name="res.users",
        string="Verifier",
        tracking=True,
        index=True,
        domain="[('id', 'in', verifier_candidate_ids)]",
        help="The Request Verifier named on this request, who gets its Todo when it "
        "reaches Awaiting Verification. Advisory only: any Request Verifier may "
        "still confirm or send the request back.",
    )
    date_verified = fields.Date(
        string="Verified Date",
        copy=False,
        readonly=True,
        tracking=True,
        help="Date the request was confirmed past Awaiting Verification. Cleared "
        "when it comes back to Awaiting Verification or Draft.",
    )
    verifier_candidate_ids = fields.Many2many(
        comodel_name="res.users",
        string="Verifier Candidates",
        compute="_compute_verifier_candidate_ids",
    )

    # "state" only so the new-record form computes it; the OU layer re-declares
    # the dependency on operating_unit_id.
    @api.depends("state")
    def _compute_verifier_candidate_ids(self):
        for rec in self:
            rec.verifier_candidate_ids = rec._get_verifier_candidates()

    def _get_verifier_candidates(self):
        """Who may be named ผู้ตรวจสอบ; extension hook (OU layer narrows).

        A plain method, not a read of ``verifier_candidate_ids``: on a new
        record that x2many reads back as new-record ids, which never
        intersect real users."""
        return self._get_duty_holders("agx_approval.group_approval_verify")

    def _get_duty_holders(self, group_xmlid):
        """Internal users who hold the approval duty ``group_xmlid``.

        System/IAM admins (``base.group_erp_manager``) are seeded into the duty
        groups, so the group's users also list them. Keep an admin only when
        another grant (their role) carries the duty too."""
        # sudo: regular users cannot read group membership
        group = self.env.ref(group_xmlid).sudo()
        admin = self.env.ref("base.group_erp_manager")

        def holds_duty(user):
            if admin not in user.groups_id:
                return True
            # A user's groups already hold every implied group, so another
            # grant carries the duty iff one of them implies it directly. No
            # walk over implied_ids, which may contain cycles.
            return any(group in g.implied_ids for g in user.groups_id - admin)

        return group.users.filtered(lambda u: not u.share and holds_duty(u))

    @api.constrains("verifier_id")
    def _check_verifier(self):
        for rec in self:
            if rec.state == "to_verify" and not rec.verifier_id:
                raise ValidationError(
                    _("Request %s is awaiting verification: a Verifier is required.")
                    % rec.name
                )
            if (
                rec.verifier_id
                and rec.verifier_id not in rec._get_verifier_candidates()
            ):
                raise ValidationError(
                    _("%(user)s is not a Request Verifier for request %(request)s.")
                    % {"user": rec.verifier_id.display_name, "request": rec.name}
                )

    def action_to_verify(self):
        # Superuser mode (demo data, hooks, sudo'ed programmatic flows) passes.
        if not self.env.su and not self.verifier_id:
            raise UserError(_("Please set the Verifier before submitting the request."))
        return super().action_to_verify()

    def write(self, vals):
        if "state" not in vals and "verifier_id" not in vals:
            return super().write(vals)
        before = {rec.id: (rec.state, rec.verifier_id) for rec in self}
        res = super().write(vals)
        for rec in self:
            rec._sync_verifier_todos(*before[rec.id])
            rec._stamp_date_verified(before[rec.id][0])
        return res

    def _stamp_date_verified(self, old_state):
        """Stamp วันที่ตรวจสอบ when the request moves on from to_verify; clear it
        whenever it comes back for (re)verification."""
        self.ensure_one()
        if self.state == old_state:
            return
        if old_state == "to_verify" and self.state not in ("draft", "rejected"):
            self.date_verified = fields.Date.context_today(self)
        elif self.state in ("draft", "to_verify") and self.date_verified:
            self.date_verified = False

    def _sync_verifier_todos(self, old_state, old_assignee):
        """Keep the to_verify and returned Todos in step with the state.

        State-driven, not button-driven: every path into or out of to_verify
        (ส่งคำขอ, ยืนยันตรวจสอบ, ตีกลับ, ดึงกลับ, reject — including the budget
        step's own ตีกลับ) passes through here."""
        self.ensure_one()
        verify_todos = self._verifier_todos(VERIFY_TODO)
        if old_state != "to_verify" and self.state == "to_verify":
            if self.verifier_id and not verify_todos:
                self.activity_schedule(
                    VERIFY_TODO,
                    summary=_("Please verify approval request %s") % self.name,
                    user_id=self.verifier_id.id,
                )
        elif old_state == "to_verify" and self.state != "to_verify":
            self._close_todos(
                verify_todos,
                done=self.env.user == old_assignee
                and self.state not in ("draft", "rejected"),
            )
        elif self.state == "to_verify" and self.verifier_id != old_assignee:
            if verify_todos:
                verify_todos.sudo().write({"user_id": self.verifier_id.id})
            elif self.verifier_id:
                self.activity_schedule(
                    VERIFY_TODO,
                    summary=_("Please verify approval request %s") % self.name,
                    user_id=self.verifier_id.id,
                )
        if self.state in ("to_verify", "rejected") and old_state != self.state:
            # Resubmitted or rejected: the presser's returned Todo is done,
            # anyone else's is simply withdrawn.
            returned = self._verifier_todos(RETURNED_TODO)
            mine = returned.filtered(
                lambda a: self.state == "to_verify" and a.user_id == self.env.user
            )
            self._close_todos(mine, done=True)
            self._close_todos(returned - mine, done=False)

    def _verifier_todos(self, xmlid):
        act_type = self.env.ref(xmlid)
        return self.sudo().activity_ids.filtered(
            lambda a: a.activity_type_id == act_type
        )

    def _close_todos(self, activities, done):
        """Mark done as the acting user (it is their own Todo), else withdraw."""
        if not activities:
            return
        if done:
            activities.sudo(False).action_feedback()
        else:
            activities.sudo().unlink()

    def _send_back(self, reason):
        was_to_verify = self.state == "to_verify"
        res = super()._send_back(reason)
        if was_to_verify and self.state == "draft":
            self._schedule_returned_todos(reason)
        return res

    def _schedule_returned_todos(self, reason):
        """ผู้ตรวจสอบตีกลับ: tell the requester and the creator to fix and resubmit."""
        self.ensure_one()
        already = self._verifier_todos(RETURNED_TODO).user_id
        users = self.owner_id.user_id | self.user_id | self.create_uid
        for user in users - already:
            if user.share or not user.active:
                continue
            self.activity_schedule(
                RETURNED_TODO,
                summary=_("Approval request %s was sent back") % self.name,
                note=reason,
                user_id=user.id,
            )
