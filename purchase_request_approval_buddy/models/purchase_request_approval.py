from odoo import api, fields, models

# States in which the Assigned Officer still follows the Buddy settings: the
# editable states plus ``pending_pr``, whose ตีกลับ/แก้ไข resync rewrites the
# requesting department before the พจ.1 flips back to draft.
_FOLLOW_BUDDY_STATES = ("draft", "sarabun_returned", "pending_pr")

# The "จัดทำรายงานขอซื้อ/จ้าง (พจ.1)" Todo. purchase_request_approval_todo
# sends it to the unit's procurement role on create, but skips a พจ.1 that
# already has one, and closes / drops it when the พจ.1 leaves draft.
_PREPARE_ACTIVITY = "purchase_request_approval_todo.mail_activity_pa_notify_procurement"


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    # ADR-0013: the Approver field was never filled; it now holds the
    # Assigned Officer (เจ้าหน้าที่ผู้รับผิดชอบ).
    assigned_to = fields.Many2one(
        string="Assigned Officer",
        compute="_compute_assigned_to",
        store=True,
        readonly=False,
        copy=False,
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref("purchase_buddy.group_purchase_buddy").ids,
            )
        ],
        help="ค่าเริ่มต้นมาจากการตั้งค่า Buddy ดูแลหน่วยงาน (ตามส่วนงานผู้ขอ) — "
        "เปลี่ยนเป็นเจ้าหน้าที่ Buddy คนอื่นได้",
    )

    @api.depends("requesting_department_id", "department_analytic_id")
    def _compute_assigned_to(self):
        """Default the officer from the Buddy settings while the พจ.1 is
        open; a row's domain may read any field, so the depends cover the
        usual ones. An officer the settings still assign is kept, so a manual
        pick survives edits that keep it covered."""
        Buddy = self.env["purchase.buddy"]
        for approval in self:
            if approval.state in _FOLLOW_BUDDY_STATES:
                buddies = Buddy._get_buddy_users(approval)
                if approval.assigned_to not in buddies:
                    approval.assigned_to = buddies[:1]
            else:
                approval.assigned_to = approval.assigned_to

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._route_prepare_activity()
        return records

    def write(self, vals):
        # The compute reads ``state``, which is not a dependency: settle a
        # pending default under the state that triggered it, or a พจ.1 that
        # leaves draft before a flush freezes an empty officer.
        if "state" in vals:
            self.flush_recordset(["assigned_to"])
        res = super().write(vals)
        if {"assigned_to", "requesting_department_id", "state"} & set(vals):
            self._route_prepare_activity()
        return res

    def _route_prepare_activity(self):
        """Give the draft พจ.1's "จัดทำ พจ.1" Todo to its Assigned Officer:
        schedule it when missing (on create, or when a ตีกลับ/แก้ไข brings the
        พจ.1 back to draft) and move an open one, role-based or not, to the
        current officer. Without an officer the role-based Todo stays."""
        act_type = self.env.ref(_PREPARE_ACTIVITY)
        for approval in self.sudo().filtered(
            lambda a: a.state == "draft" and a.assigned_to
        ):
            officer = approval.assigned_to
            activity = approval.activity_ids.filtered(
                lambda a, t=act_type: a.activity_type_id == t
            )
            if not activity:
                approval.activity_schedule(
                    _PREPARE_ACTIVITY,
                    summary="มีแบบรายงานขอให้จัดซื้อจัดจ้าง (พจ.1) %s "
                    "ถูกสร้างขึ้น กรุณาตรวจสอบ" % approval.name,
                    user_id=officer.id,
                )
            elif activity.user_id != officer:
                activity.write({"user_id": officer.id, "responsible_role_id": False})
