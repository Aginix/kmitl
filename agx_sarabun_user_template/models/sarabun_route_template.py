# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SarabunRouteTemplate(models.Model):
    _inherit = "sarabun.route.template"

    owner_id = fields.Many2one(
        "res.users",
        string="เจ้าของ (Owner)",
        default=lambda self: self.env.user,
        copy=False,
        index=True,
    )
    visibility = fields.Selection(
        [
            ("personal", "ส่วนตัว (Personal)"),
            ("unit", "ทั้งหน่วยงาน (Unit)"),
            ("public", "ทุกคน (Public)"),
        ],
        string="การมองเห็น (Visibility)",
        default=lambda self: self._default_visibility(),
        required=True,
        index=True,
    )

    def _default_visibility(self):
        if self.env.su or self.env.user.has_group(
            "agx_sarabun.group_sarabun_manager"
        ):
            return "public"
        return "personal"

    @api.constrains("visibility")
    def _check_visibility_public(self):
        if self.env.su:
            return
        for template in self:
            if template.visibility == "public" and not self.env.user.has_group(
                "agx_sarabun.group_sarabun_manager"
            ):
                raise ValidationError(
                    "เฉพาะผู้จัดการสารบรรณเท่านั้นที่สามารถตั้งค่าการมองเห็น"
                    "เป็น 'ทุกคน (Public)' ได้"
                )

    @api.constrains("visibility", "department_id")
    def _check_visibility_unit_department(self):
        for template in self:
            if template.visibility == "unit" and not template.department_id:
                raise ValidationError(
                    "กรุณาระบุหน่วยงานเมื่อเลือกการมองเห็นแบบ "
                    "'ทั้งหน่วยงาน (Unit)'"
                )
