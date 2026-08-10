from odoo import _, models

RESERVE_BUDGET_ACTIVITY = "purchase_request_todo.mail_activity_pr_reserve_budget"
AWAITING_ENDORSEMENT_LETTER_ACTIVITY = (
    "purchase_request_todo.mail_activity_pr_awaiting_endorsement_letter"
)
AWAITING_SIGNER_ACTIVITY = "purchase_request_todo.mail_activity_pr_awaiting_signer"
ENDORSEMENT_APPROVED_ACTIVITY = (
    "purchase_request_todo.mail_activity_pr_endorsement_approved"
)
BUDGET_COMMITMENT_ROLE = "budget_role.role_budget_commitment"

PR_LIFECYCLE_ACTIVITIES = [
    RESERVE_BUDGET_ACTIVITY,
    AWAITING_ENDORSEMENT_LETTER_ACTIVITY,
    AWAITING_SIGNER_ACTIVITY,
    ENDORSEMENT_APPROVED_ACTIVITY,
]


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _schedule_personal_todo(self, xmlid, user, summary):
        """Schedule a personal Todo (single assignee) if it isn't already
        raised for that user; supersede stale copies with the same
        (type, user) pair so the inbox stays free of duplicates."""
        self.ensure_one()
        act_type = self.env.ref(xmlid, raise_if_not_found=False)
        if not act_type or not user:
            return
        self.activity_ids.filtered(
            lambda a: a.activity_type_id == act_type and a.user_id.id == user.id
        ).unlink()
        self.activity_schedule(xmlid, summary=summary, user_id=user.id)

    # ---------------------------------------------------------------------
    # Reserve Budget (draft → to_verify)
    # ---------------------------------------------------------------------
    def _reserve_budget_todo_summary(self):
        """Message shown on the จองงบประมาณ Todo — names the พ.1 explicitly so
        the recipient sees which request landed in their inbox."""
        self.ensure_one()
        return _(
            "ท่านได้รับ แบบคำขอซื้อขอจ้าง (พ.1) เลขที่ %s "
            "เพื่อดำเนินการ จองเงินงบประมาณ"
        ) % (self.name or "")

    def _schedule_reserve_budget_todo(self):
        """Raise the execution Todo when the พ.1 enters รอจองงบประมาณ. Route
        to the จองงบประมาณ role of the พ.1's operating unit (role-in-unit,
        ADR-0002); if role or OU is missing, fall back to a personal Todo on
        ``requested_by`` so the flow never stalls silently."""
        act_type = self.env.ref(RESERVE_BUDGET_ACTIVITY, raise_if_not_found=False)
        role = self.env.ref(BUDGET_COMMITMENT_ROLE, raise_if_not_found=False)
        if not act_type:
            return
        for rec in self:
            if rec.activity_ids.filtered(lambda a: a.activity_type_id == act_type):
                continue  # already raised
            summary = rec._reserve_budget_todo_summary()
            if role and rec.operating_unit_id:
                rec.activity_schedule(
                    RESERVE_BUDGET_ACTIVITY,
                    summary=summary,
                    responsible_role_id=role.id,
                    operating_unit_id=rec.operating_unit_id.id,
                )
            elif rec.requested_by:
                rec.activity_schedule(
                    RESERVE_BUDGET_ACTIVITY,
                    summary=summary,
                    user_id=rec.requested_by.id,
                )

    # ---------------------------------------------------------------------
    # Awaiting endorsement letter (to_verify → to_submit)
    # ---------------------------------------------------------------------
    def _endorsement_letter_todo_summary(self):
        self.ensure_one()
        return _(
            "ท่านได้รับ แบบคำขอซื้อขอจ้าง (พ.1) เลขที่ %s "
            "เพื่อดำเนินการ สร้างหนังสือขอความเห็นชอบให้จัดหา"
        ) % (self.name or "")

    def _schedule_endorsement_letter_todo(self):
        """Route to the จองงบประมาณ role of the พ.1's operating unit; fall
        back to ``requested_by`` when the unit or role is unknown."""
        role = self.env.ref(BUDGET_COMMITMENT_ROLE, raise_if_not_found=False)
        for rec in self:
            summary = rec._endorsement_letter_todo_summary()
            if role and rec.operating_unit_id:
                rec.activity_schedule(
                    AWAITING_ENDORSEMENT_LETTER_ACTIVITY,
                    summary=summary,
                    responsible_role_id=role.id,
                    operating_unit_id=rec.operating_unit_id.id,
                )
            elif rec.requested_by:
                rec.activity_schedule(
                    AWAITING_ENDORSEMENT_LETTER_ACTIVITY,
                    summary=summary,
                    user_id=rec.requested_by.id,
                )

    # ---------------------------------------------------------------------
    # Awaiting authorized signer (to_submit → to_approve, Sarabun routing)
    # ---------------------------------------------------------------------
    def _awaiting_signer_todo_summary(self):
        self.ensure_one()
        return _(
            "แบบคำขอซื้อขอจ้าง (พ.1) เลขที่ %s "
            "รอท่านพิจารณาลงนามให้ความเห็นชอบ"
        ) % (self.name or "")

    def _schedule_awaiting_signer_todo(self, document):
        """Personal Todo per Sarabun step actor holding the pen right now —
        the ผู้มีอำนาจลงนาม. Actors are the snapshot ``actor_user_ids`` on
        the active routing step (agx_sarabun ADR-0003)."""
        if not document:
            return
        active_steps = document.routing_step_ids.filtered(
            lambda s: s.state == "active"
        )
        actors = active_steps.mapped("actor_user_ids")
        for rec in self:
            summary = rec._awaiting_signer_todo_summary()
            for user in actors:
                rec._schedule_personal_todo(
                    AWAITING_SIGNER_ACTIVITY, user, summary
                )

    # ---------------------------------------------------------------------
    # Endorsement approved (to_approve → in_approval / in_egp)
    # ---------------------------------------------------------------------
    def _endorsement_approved_todo_summary(self):
        """Body differs by procurement path: EGP recording vs standard PA
        (พจ.1) drafting."""
        self.ensure_one()
        if self.is_egp:
            return _(
                "แบบคำขอซื้อขอจ้าง (พ.1) เลขที่ %s "
                "ได้รับความเห็นชอบให้ดำเนินการจัดหาแล้ว "
                "กรุณาตรวจสอบเพื่อ บันทึกเลขที่โครงการจากระบบ EGP "
                "และบันทึกข้อมูลสัญญา/ใบสั่งซื้อ/จ้างภายในระบบ"
            ) % (self.name or "")
        return _(
            "แบบคำขอซื้อขอจ้าง (พ.1) เลขที่ %s "
            "ได้รับความเห็นชอบให้ดำเนินการจัดหาแล้ว "
            "กรุณาตรวจสอบเพื่อจัดทำ แบบรายงานขอให้จัดซื้อจัดจ้าง (พจ.1)"
        ) % (self.name or "")

    def _schedule_endorsement_approved_todo(self):
        """Route to the จองงบประมาณ role of the พ.1's operating unit; fall
        back to ``assigned_to`` when the unit or role is unknown."""
        role = self.env.ref(BUDGET_COMMITMENT_ROLE, raise_if_not_found=False)
        for rec in self:
            summary = rec._endorsement_approved_todo_summary()
            if role and rec.operating_unit_id:
                rec.activity_schedule(
                    ENDORSEMENT_APPROVED_ACTIVITY,
                    summary=summary,
                    responsible_role_id=role.id,
                    operating_unit_id=rec.operating_unit_id.id,
                )
            elif rec.assigned_to:
                rec.activity_schedule(
                    ENDORSEMENT_APPROVED_ACTIVITY,
                    summary=summary,
                    user_id=rec.assigned_to.id,
                )

    # ---------------------------------------------------------------------
    # State-transition hooks
    # ---------------------------------------------------------------------
    def button_to_verify(self):
        res = super().button_to_verify()
        # Only schedule for records that actually landed at to_verify: super may
        # short-circuit (exceptions popup) or divert (purchase_request_verify_state
        # routes to to_examine when verification is enabled).
        self.filtered(
            lambda r: r.state == "to_verify"
        )._schedule_reserve_budget_todo()
        return res

    def button_to_submit(self):
        res = super().button_to_submit()
        landed = self.filtered(lambda r: r.state == "to_submit")
        # Reserve-budget step is genuinely done → Completed history.
        landed.activity_feedback([RESERVE_BUDGET_ACTIVITY])
        # Next-actor Todo: draft the endorsement letter.
        landed._schedule_endorsement_letter_todo()
        return res

    def _on_sarabun_circulating(self, document):
        res = super()._on_sarabun_circulating(document)
        landed = self.filtered(lambda r: r.state == "to_approve")
        # Endorsement letter has been drafted (Sarabun is now circulating it).
        landed.activity_feedback([AWAITING_ENDORSEMENT_LETTER_ACTIVITY])
        landed._schedule_awaiting_signer_todo(document)
        return res

    def _on_sarabun_completed(self, document):
        res = super()._on_sarabun_completed(document)
        landed = self.filtered(lambda r: r.state in ("in_approval", "in_egp"))
        # ผู้มีอำนาจลงนาม signed → close their Todo.
        landed.activity_feedback([AWAITING_SIGNER_ACTIVITY])
        landed._schedule_endorsement_approved_todo()
        return res

    def _on_sarabun_rejected(self, document, step):
        res = super()._on_sarabun_rejected(document, step)
        # Sarabun bounced back — the signer's pending Todo no longer applies.
        self.activity_unlink([AWAITING_SIGNER_ACTIVITY])
        return res

    def button_draft(self):
        res = super().button_draft()
        # Reset — no execution happened; drop every open lifecycle Todo silently.
        self.activity_unlink(PR_LIFECYCLE_ACTIVITIES)
        return res

    def _action_do_cancel(self, reason):
        res = super()._action_do_cancel(reason)
        self.activity_unlink(PR_LIFECYCLE_ACTIVITIES)
        return res
