from odoo import _, models

EGP_NUMBER_ENTRY_ACTIVITY = (
    "purchase_request_egp_todo.mail_activity_pr_egp_number_entry"
)
PROCUREMENT_ROLE = "purchase_user_role.purchase_role_procurement"


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

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

    def _on_sarabun_completed(self, document):
        res = super()._on_sarabun_completed(document)
        landed = self.filtered(lambda r: r.state in ("in_approval", "in_egp"))
        landed.filtered(lambda r: r.is_egp)._schedule_egp_todo()
        return res
