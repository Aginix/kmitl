from odoo import _, fields, models
from odoo.osv import expression


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    approval_request_count = fields.Integer(
        string="คำขออนุมัติ",
        compute="_compute_approval_request_count",
    )

    def _approval_request_domain(self):
        """คำขอที่พนักงานคนนี้เป็นผู้ขอ (owner_id) หรืออยู่ในรายชื่อผ่าน
        work_contact_id — รวมแบบไม่ซ้ำ เพราะผู้ขอมักถูกใส่ในรายชื่อของตัวเองด้วย."""
        self.ensure_one()
        domain = [("owner_id", "=", self.id)]
        if self.work_contact_id:
            domain = expression.OR(
                [domain, [("participant_ids.partner_id", "=", self.work_contact_id.id)]]
            )
        return domain

    def _compute_approval_request_count(self):
        # sudo เฉพาะการนับ เพื่อให้ badge แสดงยอดจริงแม้ record rule
        # (own-only / OU) จะซ่อนบางรายการจากผู้ใช้คนนี้; ตอนคลิกปุ่ม
        # action_view_approval_requests ยังวิ่งด้วยสิทธิ์ของผู้ใช้เอง
        Request = self.env["approval.request"].sudo()
        for employee in self:
            origin = employee._origin
            employee.approval_request_count = (
                Request.search_count(origin._approval_request_domain()) if origin else 0
            )

    def action_view_approval_requests(self):
        self.ensure_one()
        domain = self._approval_request_domain()
        requests = self.env["approval.request"].search(domain)
        action = {
            "type": "ir.actions.act_window",
            "name": _("คำขออนุมัติ"),
            "res_model": "approval.request",
            "domain": domain,
            "context": {"create": False},
        }
        if len(requests) == 1:
            action.update(view_mode="form", res_id=requests.id)
        else:
            action["view_mode"] = "tree,form"
        return action
