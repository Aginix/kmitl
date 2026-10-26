from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

RESERVE_TODO = "agx_approval_budget_todo.mail_activity_reserve_budget"


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # ผู้ยืนยันงบประมาณ: the one Budget Confirmer named on this request,
    # who gets its to_commit Todo. Any member of the group may still act.
    budget_verifier_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ยืนยันงบประมาณ",
        copy=False,
        tracking=True,
        index=True,
        domain="[('id', 'in', budget_verifier_candidate_ids)]",
    )
    date_budget_committed = fields.Date(
        string="วันที่ยืนยันงบประมาณ",
        copy=False,
        readonly=True,
        tracking=True,
        help="วันที่ยืนยันงบประมาณ (รอยืนยันงบประมาณ → ขั้นถัดไป); ล้างเมื่อคำขอ"
        "ย้อนกลับมาก่อนหรือที่ขั้นรอยืนยันงบประมาณ",
    )
    budget_verifier_candidate_ids = fields.Many2many(
        comodel_name="res.users",
        compute="_compute_budget_verifier_candidate_ids",
    )

    # "state" only so the new-record form computes it; the OU layer re-declares
    # the dependency on operating_unit_id.
    @api.depends("state")
    def _compute_budget_verifier_candidate_ids(self):
        for rec in self:
            rec.budget_verifier_candidate_ids = rec._get_budget_verifier_candidates()

    def _get_budget_verifier_candidates(self):
        """Who may be named ผู้ยืนยันงบประมาณ; extension hook (OU layer
        narrows). A plain method for the same reason as
        ``_get_verifier_candidates``."""
        return self._get_duty_holders("agx_approval.group_approval_budget_commit")

    @api.constrains("budget_verifier_id")
    def _check_budget_verifier(self):
        for rec in self:
            if rec.state == "to_commit" and not rec.budget_verifier_id:
                raise ValidationError(
                    _("คำขอ %s อยู่ระหว่างรอยืนยันงบประมาณ ต้องระบุผู้ยืนยันงบประมาณ") % rec.name
                )
            if (
                rec.budget_verifier_id
                and rec.budget_verifier_id not in rec._get_budget_verifier_candidates()
            ):
                raise ValidationError(
                    _("%(user)s ไม่ใช่ผู้ยืนยันงบประมาณคำขออนุมัติ %(request)s")
                    % {"user": rec.budget_verifier_id.display_name, "request": rec.name}
                )

    def action_confirm_verify(self):
        # Superuser mode passes, as in agx_approval_verifier.action_to_verify.
        if not self.env.su and any(
            r.state == "to_verify" and not r.budget_verifier_id for r in self
        ):
            raise UserError(_("กรุณาระบุผู้ยืนยันงบประมาณก่อนยืนยันตรวจสอบ"))
        return super().action_confirm_verify()

    def write(self, vals):
        if "state" not in vals and "budget_verifier_id" not in vals:
            return super().write(vals)
        before = {rec.id: (rec.state, rec.budget_verifier_id) for rec in self}
        res = super().write(vals)
        for rec in self:
            rec._sync_budget_verifier_todos(*before[rec.id])
            rec._stamp_date_budget_committed(before[rec.id][0])
        return res

    def _stamp_date_budget_committed(self, old_state):
        """Stamp วันที่ยืนยันงบประมาณ when the request moves on from to_commit
        (reserved/drawn); clear it whenever it comes back to or before that step."""
        self.ensure_one()
        if self.state == old_state:
            return
        if old_state == "to_commit" and self.state not in (
            "draft",
            "to_verify",
            "rejected",
        ):
            self.date_budget_committed = fields.Date.context_today(self)
        elif (
            self.state in ("draft", "to_verify", "to_commit")
            and self.date_budget_committed
        ):
            self.date_budget_committed = False

    def _sync_budget_verifier_todos(self, old_state, old_assignee):
        """Keep the reserve Todo in step with to_commit.

        State-driven like ``_sync_verifier_todos``: ยืนยันตรวจสอบ, ยืนยันงบประมาณ,
        ตีกลับ, ดึงกลับ, reset and reject all pass through here."""
        self.ensure_one()
        todos = self._verifier_todos(RESERVE_TODO)
        if old_state != "to_commit" and self.state == "to_commit":
            if self.budget_verifier_id and not todos:
                self.activity_schedule(
                    RESERVE_TODO,
                    summary=_("กรุณายืนยันงบประมาณ สำหรับคำขออนุมัติเลขที่ %s") % self.name,
                    user_id=self.budget_verifier_id.id,
                )
        elif old_state == "to_commit" and self.state != "to_commit":
            # Moving forward (reserved/drawn) is the only "done"; ตีกลับ,
            # ดึงกลับ and reject withdraw it.
            self._close_todos(
                todos,
                done=self.env.user == old_assignee
                and self.state not in ("draft", "to_verify", "rejected"),
            )
        elif self.state == "to_commit" and self.budget_verifier_id != old_assignee:
            if todos:
                todos.sudo().write({"user_id": self.budget_verifier_id.id})
            elif self.budget_verifier_id:
                self.activity_schedule(
                    RESERVE_TODO,
                    summary=_("กรุณายืนยันงบประมาณ สำหรับคำขออนุมัติเลขที่ %s") % self.name,
                    user_id=self.budget_verifier_id.id,
                )
