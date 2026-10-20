from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

VERIFY_TODO = "purchase_request_verifier.mail_activity_pr_verify"
RETURNED_TODO = "purchase_request_verifier.mail_activity_pr_returned"


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    # ผู้ยืนยันตรวจสอบ (ADR-0011): the one Verifier named on this พ.1, who gets
    # its to_verify Todo. Any member of the Verifier group may still act.
    assigned_to = fields.Many2one(
        string="ผู้ยืนยันตรวจสอบ",
        domain="[('id', 'in', verifier_candidate_ids)]",
    )
    verifier_candidate_ids = fields.Many2many(
        comodel_name="res.users",
        compute="_compute_verifier_candidate_ids",
    )

    @api.depends("operating_unit_id")
    def _compute_verifier_candidate_ids(self):
        for rec in self:
            rec.verifier_candidate_ids = rec._get_verifier_candidates()

    def _get_verifier_candidates(self):
        """Who may be named ผู้ยืนยันตรวจสอบ; extension hook (OU layer narrows).

        A plain method, not a read of ``verifier_candidate_ids``: on a new
        record that x2many reads back as new-record ids, which never
        intersect real users."""
        return self._get_duty_holders(
            "purchase_request_kmitl.group_purchase_request_verify"
        )

    def _get_duty_holders(self, group_xmlid):
        """Internal users who hold the PR duty ``group_xmlid``.

        ``base.group_erp_manager`` implies the PR duty groups, so the group's
        users also list every system/IAM admin. Keep an admin only when another
        grant (their role) carries the duty too."""
        # sudo: regular users cannot read group membership
        group = self.env.ref(group_xmlid).sudo()
        admin = self.env.ref("base.group_erp_manager")
        cache = {}

        def carries(g):
            # Implies the duty along a path that does not pass through admin
            if g not in cache:
                implied = g.implied_ids - admin
                cache[g] = group in implied or any(carries(h) for h in implied)
            return cache[g]

        def holds_duty(user):
            if admin not in user.groups_id:
                return True
            return any(carries(g) for g in user.groups_id - admin)

        return group.users.filtered(lambda u: not u.share and holds_duty(u))

    @api.constrains("assigned_to", "operating_unit_id")
    def _check_assigned_to_verifier(self):
        for rec in self:
            if rec.state == "to_verify" and not rec.assigned_to:
                raise ValidationError(
                    _("คำขอ %s อยู่ระหว่างรอตรวจสอบ ต้องระบุผู้ยืนยันตรวจสอบ") % rec.name
                )
            if (
                rec.assigned_to
                and rec.assigned_to not in rec._get_verifier_candidates()
            ):
                raise ValidationError(
                    _("%(user)s ไม่ใช่ผู้ตรวจสอบแบบขอให้จัดหา (พ.1) ของคำขอ %(pr)s")
                    % {"user": rec.assigned_to.display_name, "pr": rec.name}
                )

    @api.onchange("operating_unit_id")
    def _onchange_verifier_candidates(self):
        candidates = self._get_verifier_candidates()
        if self.assigned_to and self.assigned_to not in candidates:
            self.assigned_to = False
        if not self.assigned_to and len(candidates) == 1:
            self.assigned_to = candidates

    def button_to_verify(self):
        if not self.assigned_to:
            raise UserError(_("กรุณาระบุผู้ยืนยันตรวจสอบก่อนส่งคำขอ"))
        return super().button_to_verify()

    def write(self, vals):
        if "state" not in vals and "assigned_to" not in vals:
            return super().write(vals)
        before = {rec.id: (rec.state, rec.assigned_to) for rec in self}
        res = super().write(vals)
        for rec in self:
            rec._sync_verifier_todos(*before[rec.id])
        return res

    def _sync_verifier_todos(self, old_state, old_assignee):
        """Keep the to_verify and returned Todos in step with the state (ADR-0011).

        State-driven, not button-driven: every path into or out of to_verify
        (submit, ตรวจสอบ, ตีกลับ, ดึงกลับ, cancel — including the budget step's
        own writes) passes through here."""
        self.ensure_one()
        verify_todos = self._verifier_todos(VERIFY_TODO)
        if old_state != "to_verify" and self.state == "to_verify":
            if self.assigned_to and not verify_todos:
                self.activity_schedule(
                    VERIFY_TODO,
                    summary=_("กรุณาตรวจสอบแบบขอให้จัดหา (พ.1) เลขที่ %s") % self.name,
                    user_id=self.assigned_to.id,
                )
        elif old_state == "to_verify" and self.state != "to_verify":
            self._close_todos(
                verify_todos,
                done=self.env.user == old_assignee
                and self.state not in ("draft", "cancelled"),
            )
        elif self.state == "to_verify" and self.assigned_to != old_assignee:
            verify_todos.sudo().write({"user_id": self.assigned_to.id})
        if self.state in ("to_verify", "cancelled") and old_state != self.state:
            # Resubmitted or cancelled: the presser's returned Todo is done,
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

    def _action_do_return_to_draft(self, reason):
        was_to_verify = self.state == "to_verify"
        res = super()._action_do_return_to_draft(reason)
        if was_to_verify and self.state == "draft":
            self._schedule_returned_todos(reason)
        return res

    def _schedule_returned_todos(self, reason):
        """ผู้ตรวจสอบตีกลับ: tell the requester and the creator to fix and resubmit."""
        self.ensure_one()
        already = self._verifier_todos(RETURNED_TODO).user_id
        for user in (self.requested_by | self.create_uid) - already:
            if user.share or not user.active:
                continue
            self.activity_schedule(
                RETURNED_TODO,
                summary=_("แบบขอให้จัดหา (พ.1) เลขที่ %s ถูกตีกลับ") % self.name,
                note=reason,
                user_id=user.id,
            )
