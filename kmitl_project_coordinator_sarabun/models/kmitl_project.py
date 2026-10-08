from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    can_submit_sarabun = fields.Boolean(
        compute="_compute_can_submit_sarabun",
        help="ผู้ใช้ปัจจุบันสร้างหนังสือขออนุมัติจัดโครงการได้: หัวหน้าโครงการ "
        "ผู้ประสานงาน ผู้สร้างโครงการ หรือเจ้าหน้าที่ (Officer)",
    )

    @api.depends_context("uid")
    @api.depends("is_project_owner")
    def _compute_can_submit_sarabun(self):
        is_officer = self.env.user.has_group(
            "kmitl_project.group_kmitl_project_user_all"
        )
        for rec in self:
            rec.can_submit_sarabun = is_officer or rec.is_project_owner

    def _sarabun_submit_guard(self):
        allowed = super()._sarabun_submit_guard()
        if allowed and not self.can_submit_sarabun:
            raise AccessError(
                _(
                    "เฉพาะหัวหน้าโครงการ ผู้ประสานงาน ผู้สร้างโครงการ หรือเจ้าหน้าที่ "
                    "เท่านั้นที่สร้างหนังสือขออนุมัติจัดโครงการได้"
                )
            )
        return allowed
