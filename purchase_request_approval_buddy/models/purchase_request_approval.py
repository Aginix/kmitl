from odoo import api, fields, models

# States in which the Assigned Officer still follows the Buddy settings: the
# editable states plus ``pending_pr``, whose ตีกลับ/แก้ไข resync rewrites the
# requesting department before the พจ.1 flips back to draft.
_FOLLOW_BUDDY_STATES = ("draft", "sarabun_returned", "pending_pr")


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

    def write(self, vals):
        # The compute reads ``state``, which is not a dependency: settle a
        # pending default under the state that triggered it, or a พจ.1 that
        # leaves draft before a flush freezes an empty officer.
        if "state" in vals:
            self.flush_recordset(["assigned_to"])
        return super().write(vals)
