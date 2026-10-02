from odoo import models, _

# Maps (old_state, new_state) → (subject_fn, body_fn).
# "*" as old_state matches any previous state.
# Keys are checked in order; first match wins.
_STATE_NOTIFICATIONS = [
    (
        ("to_verify_budget", "to_approve"),
        lambda r: (
            _("จองงบประมาณเสร็จสิ้น: %s") % r.name,
            _("ใบขอให้จัดหา %s ผ่านขั้นตอนรอจองงบประมาณแล้ว และพร้อมสำหรับการอนุมัติ")
            % r.name,
        ),
    ),
    (
        ("in_approval", "in_progress"),
        lambda r: (
            _("ได้รับการอนุมัติ: %s") % r.name,
            _("ใบขอให้จัดหา %s ได้รับการอนุมัติแล้ว") % r.name,
        ),
    ),
    (
        ("*", "rejected"),
        lambda r: (
            _("ถูกตีกลับ: %s") % r.name,
            _("ใบขอให้จัดหา %s ถูกตีกลับ กรุณาตรวจสอบและแก้ไข") % r.name,
        ),
    ),
    (
        ("*", "cancelled"),
        lambda r: (
            _("ถูกยกเลิก: %s") % r.name,
            _("ใบขอให้จัดหา %s ถูกยกเลิก") % r.name,
        ),
    ),
    (
        ("in_progress", "done"),
        lambda r: (
            _("เสร็จสมบูรณ์: %s") % r.name,
            _("ใบขอให้จัดหา %s ดำเนินการเสร็จสมบูรณ์แล้ว") % r.name,
        ),
    ),
]


def _match_notification(old_state, new_state):
    for (old, new), fn in _STATE_NOTIFICATIONS:
        if new != new_state:
            continue
        if old == "*" or old == old_state:
            return fn
    return None


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def write(self, vals):
        old_states = (
            {r.id: r.state for r in self} if "state" in vals else {}
        )
        res = super().write(vals)
        if not old_states:
            return res
        for rec in self:
            fn = _match_notification(old_states[rec.id], rec.state)
            if fn and rec.user_id:
                subject, body = fn(rec)
                rec._notify_workflow_event(rec.user_id, subject, body)
        return res
