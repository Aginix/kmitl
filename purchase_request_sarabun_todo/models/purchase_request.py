from odoo import _, models

AWAITING_ENDORSEMENT_LETTER_ACTIVITY = (
    "purchase_request_sarabun_todo.mail_activity_pr_awaiting_endorsement_letter"
)
AWAITING_SIGNER_ACTIVITY = (
    "purchase_request_sarabun_todo.mail_activity_pr_awaiting_signer"
)
ENDORSEMENT_APPROVED_ACTIVITY = (
    "purchase_request_todo.mail_activity_pr_endorsement_approved"
)
PROCUREMENT_ROLE = "purchase_user_role.purchase_role_procurement"


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _schedule_personal_todo(self, xmlid, user, summary):
        self.ensure_one()
        act_type = self.env.ref(xmlid, raise_if_not_found=False)
        if not act_type or not user:
            return
        self.activity_ids.filtered(
            lambda a: a.activity_type_id == act_type and a.user_id.id == user.id
        ).unlink()
        self.activity_schedule(xmlid, summary=summary, user_id=user.id)

    # ---------------------------------------------------------------------
    # Awaiting authorized signer (Sarabun circulating)
    # ---------------------------------------------------------------------
    def _awaiting_signer_todo_summary(self):
        self.ensure_one()
        return _(
            "แบบขอให้จัดหา (พ.1) เลขที่ %s "
            "รอท่านพิจารณาลงนามให้ความเห็นชอบ"
        ) % (self.name or "")

    def _schedule_awaiting_signer_todo(self, document):
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
    # Endorsement approved (Sarabun completed)
    # ---------------------------------------------------------------------
    def _endorsement_approved_todo_summary(self):
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
    # Sarabun hooks
    # ---------------------------------------------------------------------
    def _on_sarabun_circulating(self, document):
        res = super()._on_sarabun_circulating(document)
        landed = self.filtered(lambda r: r.state == "to_approve")
        landed.activity_feedback([AWAITING_ENDORSEMENT_LETTER_ACTIVITY])
        landed._schedule_awaiting_signer_todo(document)
        return res

    def _on_sarabun_completed(self, document):
        res = super()._on_sarabun_completed(document)
        landed = self.filtered(lambda r: r.state in ("in_approval", "in_egp"))
        landed.activity_feedback([AWAITING_SIGNER_ACTIVITY])
        landed._schedule_endorsement_approved_todo()
        return res

    def _on_sarabun_rejected(self, document, step):
        res = super()._on_sarabun_rejected(document, step)
        self.activity_unlink([AWAITING_SIGNER_ACTIVITY])
        return res
