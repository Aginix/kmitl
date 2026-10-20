from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

RESERVE_TODO = "purchase_request_budget_todo.mail_activity_pr_reserve_budget"


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    # ผู้ยืนยันงบประมาณ (ADR-0012): the one Budget Committer named on this พ.1,
    # who gets its to_verify_budget Todo. Any member of the group may still act.
    budget_verifier_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ยืนยันงบประมาณ",
        tracking=True,
        domain="[('id', 'in', budget_verifier_candidate_ids)]",
    )
    budget_verifier_candidate_ids = fields.Many2many(
        comodel_name="res.users",
        compute="_compute_budget_verifier_candidate_ids",
    )

    @api.depends("operating_unit_id")
    def _compute_budget_verifier_candidate_ids(self):
        for rec in self:
            rec.budget_verifier_candidate_ids = rec._get_budget_verifier_candidates()

    def _get_budget_verifier_candidates(self):
        """Who may be named ผู้ยืนยันงบประมาณ; extension hook (OU layer narrows).

        A plain method for the same reason as ``_get_verifier_candidates``."""
        group = self.env.ref(
            "purchase_request_budget.group_purchase_request_budget_commit"
        )
        # sudo: regular users cannot read group membership
        return group.sudo().users.filtered(lambda u: not u.share)

    @api.constrains("budget_verifier_id", "operating_unit_id")
    def _check_budget_verifier(self):
        for rec in self:
            if rec.state == "to_verify_budget" and not rec.budget_verifier_id:
                raise ValidationError(
                    _("คำขอ %s อยู่ระหว่างรอจองงบประมาณ ต้องระบุผู้ยืนยันงบประมาณ") % rec.name
                )
            if (
                rec.budget_verifier_id
                and rec.budget_verifier_id not in rec._get_budget_verifier_candidates()
            ):
                raise ValidationError(
                    _("%(user)s ไม่ใช่ผู้จองงบประมาณแบบขอให้จัดหา (พ.1) ของคำขอ %(pr)s")
                    % {"user": rec.budget_verifier_id.display_name, "pr": rec.name}
                )

    @api.onchange("operating_unit_id")
    def _onchange_budget_verifier_candidates(self):
        candidates = self._get_budget_verifier_candidates()
        if self.budget_verifier_id and self.budget_verifier_id not in candidates:
            self.budget_verifier_id = False
        if not self.budget_verifier_id and len(candidates) == 1:
            self.budget_verifier_id = candidates

    def button_to_approve(self):
        if any(r.state == "to_verify" and not r.budget_verifier_id for r in self):
            raise UserError(_("กรุณาระบุผู้ยืนยันงบประมาณก่อนกดตรวจสอบ"))
        return super().button_to_approve()

    def write(self, vals):
        if "state" not in vals and "budget_verifier_id" not in vals:
            return super().write(vals)
        before = {rec.id: (rec.state, rec.budget_verifier_id) for rec in self}
        res = super().write(vals)
        for rec in self:
            rec._sync_budget_verifier_todos(*before[rec.id])
        return res

    def _sync_budget_verifier_todos(self, old_state, old_assignee):
        """Keep the reserve Todo in step with to_verify_budget (ADR-0012).

        State-driven like ``_sync_verifier_todos``: ตรวจสอบ, Reserve, ตีกลับ,
        ดึงกลับ, reset and cancel all pass through here."""
        self.ensure_one()
        todos = self._verifier_todos(RESERVE_TODO)
        if old_state != "to_verify_budget" and self.state == "to_verify_budget":
            if self.budget_verifier_id and not todos:
                self.activity_schedule(
                    RESERVE_TODO,
                    summary=_("กรุณาจองงบประมาณ สำหรับแบบขอให้จัดหา (พ.1) เลขที่ %s")
                    % self.name,
                    user_id=self.budget_verifier_id.id,
                )
        elif old_state == "to_verify_budget" and self.state != "to_verify_budget":
            self._close_todos(
                todos,
                done=self.env.user == old_assignee and self.state == "to_approve",
            )
        elif (
            self.state == "to_verify_budget" and self.budget_verifier_id != old_assignee
        ):
            todos.sudo().write({"user_id": self.budget_verifier_id.id})
