from odoo import api, fields, models


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    coordinator_id = fields.Many2one(
        "res.users",
        string="ผู้ประสานงาน",
        tracking=True,
        copy=False,
        domain=lambda self: [
            ("share", "=", False),
            (
                "groups_id",
                "in",
                self.env.ref("kmitl_project.group_kmitl_project_user").id,
            ),
        ],
        help="ผู้ประสานงานโครงการ ได้รับแจ้งเมื่อสถานะโครงการเปลี่ยน "
        "และเข้าถึง/แก้ไขโครงการได้เช่นเดียวกับหัวหน้าโครงการ",
    )
    is_project_owner = fields.Boolean(
        compute="_compute_is_project_owner",
        help="ผู้ใช้ปัจจุบันเป็นหัวหน้าโครงการ ผู้ประสานงาน หรือผู้สร้างโครงการ",
    )

    @api.depends_context("uid")
    @api.depends("manager_id", "coordinator_id", "creating_user_id")
    def _compute_is_project_owner(self):
        user = self.env.user
        for rec in self:
            owners = (
                rec.manager_id.sudo().user_id
                | rec.coordinator_id
                | rec.creating_user_id
            )
            rec.is_project_owner = user in owners

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._subscribe_coordinator()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get("coordinator_id"):
            self._subscribe_coordinator()
        return res

    def _subscribe_coordinator(self):
        """Make the coordinator a follower receiving status changes. A partner
        already following (e.g. the creator) gets the status subtype added rather
        than its subtypes replaced; a previous coordinator is left subscribed."""
        subtype = self.env.ref("kmitl_project_coordinator.mt_kmitl_project_state")
        for rec in self.filtered("coordinator_id"):
            partner = rec.coordinator_id.partner_id
            follower = rec.message_follower_ids.filtered(
                lambda f, p=partner: f.partner_id == p
            )
            if follower:
                follower.sudo().subtype_ids = [(4, subtype.id)]
            else:
                rec.message_subscribe(partner_ids=partner.ids)

    def _track_subtype(self, init_values):
        self.ensure_one()
        if "state" in init_values:
            return self.env.ref("kmitl_project_coordinator.mt_kmitl_project_state")
        return super()._track_subtype(init_values)
