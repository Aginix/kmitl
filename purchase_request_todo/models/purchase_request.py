from odoo import _, models

AWAITING_SIGNER_ACTIVITY = "purchase_request_todo.mail_activity_pr_awaiting_signer"
ENDORSEMENT_APPROVED_ACTIVITY = (
    "purchase_request_todo.mail_activity_pr_endorsement_approved"
)
EGP_NUMBER_ENTRY_ACTIVITY = (
    "purchase_request_todo.mail_activity_pr_egp_number_entry"
)
PROCUREMENT_ROLE = "purchase_user_role.purchase_role_procurement"


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
    # Awaiting authorized signer (to_submit → to_approve, Sarabun routing)
    # ---------------------------------------------------------------------
    def _awaiting_signer_todo_summary(self):
        self.ensure_one()
        return _(
            "แบบขอให้จัดหา (พ.1) เลขที่ %s "
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
        """Body differs by procurement path: EGP path vs standard PA (พจ.1) drafting."""
        self.ensure_one()
        if self.is_egp:
            return _(
                "แบบขอให้จัดหา (พ.1) เลขที่ %s "
                "ได้รับความเห็นชอบให้ดำเนินการจัดหาแล้ว "
                "กรุณาดำเนินการต่อในระบบ e-GP"
            ) % (self.name or "")
        return _(
            "แบบขอให้จัดหา (พ.1) เลขที่ %s "
            "ได้รับความเห็นชอบให้ดำเนินการจัดหาแล้ว "
            "กรุณาตรวจสอบเพื่อจัดทำ แบบรายงานขอให้จัดซื้อจัดจ้าง (พจ.1)"
        ) % (self.name or "")

    def _schedule_endorsement_approved_todo(self):
        """Route to the เจ้าหน้าที่พัสดุหน่วยงาน role of the พ.1's operating unit;
        fall back to ``assigned_to`` when the unit or role is unknown."""
        role = self.env.ref(PROCUREMENT_ROLE, raise_if_not_found=False)
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
    # E-GP number entry (in_egp — waiting for e-GP project number)
    # ---------------------------------------------------------------------
    def _egp_number_entry_todo_summary(self):
        self.ensure_one()
        return _(
            "แบบขอให้จัดหา (พ.1) เลขที่ %s "
            "กรุณาดำเนินการกรอกเลขที่โครงการ e-GP และกด ดำเนินการ e-GP เพื่อดำเนินการต่อ"
        ) % (self.name or "")

    def _schedule_egp_todo(self):
        """Route to the เจ้าหน้าที่พัสดุหน่วยงาน role of the พ.1's operating unit;
        fall back to ``assigned_to`` when the unit or role is unknown."""
        role = self.env.ref(PROCUREMENT_ROLE, raise_if_not_found=False)
        for rec in self:
            summary = rec._egp_number_entry_todo_summary()
            if role and rec.operating_unit_id:
                rec.activity_schedule(
                    EGP_NUMBER_ENTRY_ACTIVITY,
                    summary=summary,
                    responsible_role_id=role.id,
                    operating_unit_id=rec.operating_unit_id.id,
                )
            elif rec.assigned_to:
                rec.activity_schedule(
                    EGP_NUMBER_ENTRY_ACTIVITY,
                    summary=summary,
                    user_id=rec.assigned_to.id,
                )

    # ---------------------------------------------------------------------
    # Sarabun hooks (require document parameter — cannot be base.automation)
    # ---------------------------------------------------------------------
    def _on_sarabun_circulating(self, document):
        res = super()._on_sarabun_circulating(document)
        landed = self.filtered(lambda r: r.state == "to_approve")
        landed.activity_feedback(
            ["purchase_request_todo.mail_activity_pr_awaiting_endorsement_letter"]
        )
        landed._schedule_awaiting_signer_todo(document)
        return res

    def _on_sarabun_completed(self, document):
        res = super()._on_sarabun_completed(document)
        landed = self.filtered(lambda r: r.state in ("in_approval", "in_egp"))
        landed.activity_feedback([AWAITING_SIGNER_ACTIVITY])
        landed._schedule_endorsement_approved_todo()
        landed.filtered(lambda r: r.is_egp)._schedule_egp_todo()
        return res

    def _on_sarabun_rejected(self, document, step):
        res = super()._on_sarabun_rejected(document, step)
        self.activity_unlink([AWAITING_SIGNER_ACTIVITY])
        return res
