from odoo import api, fields, models


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    coordinator_ids = fields.Many2many(
        "res.users",
        "kmitl_project_coordinator_rel",
        "project_id",
        "user_id",
        string="ผู้ประสานงาน",
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
    # Odoo 16 does not track many2many changes — log them through a mirror.
    coordinator_names = fields.Char(
        string="ผู้ประสานงาน (ชื่อ)",
        compute="_compute_coordinator_names",
        store=True,
        tracking=True,
    )
    is_project_owner = fields.Boolean(
        compute="_compute_is_project_owner",
        help="ผู้ใช้ปัจจุบันเป็นหัวหน้าโครงการ ผู้ประสานงาน หรือผู้สร้างโครงการ",
    )
    # An owner from another OU can open the project, but the budget OU rules hide
    # its commitment / budget moves (stamped with the project's OU) — compute the
    # budget figures as sudo so they don't read 0.
    budget_reserved = fields.Float(compute_sudo=True)
    budget_remaining = fields.Float(compute_sudo=True)
    budget_commitment_count = fields.Integer(compute_sudo=True)
    budget_move_line_count = fields.Integer(compute_sudo=True)

    @api.depends("coordinator_ids.name")
    def _compute_coordinator_names(self):
        for rec in self:
            rec.coordinator_names = ", ".join(rec.coordinator_ids.mapped("name"))

    @api.depends_context("uid")
    @api.depends("manager_id", "coordinator_ids", "creating_user_id")
    def _compute_is_project_owner(self):
        user = self.env.user
        for rec in self:
            owners = (
                rec.manager_id.sudo().user_id
                | rec.coordinator_ids
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
        if vals.get("coordinator_ids"):
            self._subscribe_coordinator()
        return res

    def _subscribe_coordinator(self):
        """Make every coordinator a follower receiving status changes. A partner
        already following (e.g. the creator) gets the status subtype added rather
        than its subtypes replaced; a removed coordinator is left subscribed."""
        subtype = self.env.ref("kmitl_project_coordinator.mt_kmitl_project_state")
        for rec in self:
            partners = rec.coordinator_ids.partner_id
            followers = rec.message_follower_ids.filtered(
                lambda f, p=partners: f.partner_id in p
            )
            followers.sudo().subtype_ids = [(4, subtype.id)]
            new_partners = partners - followers.partner_id
            if new_partners:
                rec.message_subscribe(partner_ids=new_partners.ids)

    def _track_subtype(self, init_values):
        self.ensure_one()
        if "state" in init_values:
            return self.env.ref("kmitl_project_coordinator.mt_kmitl_project_state")
        return super()._track_subtype(init_values)
