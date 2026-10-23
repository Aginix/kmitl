from odoo import _, api, fields, models


class WorkCenterArea(models.Model):
    """A work area (ระบบงาน) — งานพัสดุ, งานการเงิน, … Every ศูนย์งาน belongs to
    exactly one area, and each area has its own overview. Bridges seed the area
    and add the document models it covers."""

    _name = "work.center.area"
    _description = "Work Area"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    model_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="work_center_area_ir_model_rel",
        column1="area_id",
        column2="model_id",
        string="Document Models",
        ondelete="cascade",
        groups="work_center.group_work_center_manager",
        help="Document models whose work this area divides. Seeded by the "
        "bridge modules.",
    )
    unassigned_work_center_id = fields.Many2one(
        comodel_name="work.center",
        compute="_compute_unassigned_work_center_id",
        help="The synthetic 'ยังไม่มีศูนย์งาน' card of this area.",
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)", "The work area code must be unique."),
    ]

    def _compute_unassigned_work_center_id(self):
        WorkCenter = self.env["work.center"].with_context(active_test=False)
        for area in self:
            area.unassigned_work_center_id = WorkCenter.search(
                [("area_id", "=", area.id), ("is_unassigned", "=", True)], limit=1
            )

    @api.model_create_multi
    def create(self, vals_list):
        areas = super().create(vals_list)
        self.env["work.center"].sudo().create(
            [
                {
                    "name": _("ยังไม่มีศูนย์งาน"),
                    "area_id": area.id,
                    "is_unassigned": True,
                    "sequence": 0,
                }
                for area in areas
            ]
        )
        return areas

    def unlink(self):
        self.env["work.center"].sudo().with_context(
            active_test=False, work_center_area_unlink=True
        ).search([("area_id", "in", self.ids), ("is_unassigned", "=", True)]).unlink()
        return super().unlink()
