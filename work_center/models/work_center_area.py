from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class WorkCenterArea(models.Model):
    """A work area (ระบบงาน) — งานการเงิน, งานงบประมาณ, … Every station belongs to
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
        string="Unassigned Card",
        compute="_compute_unassigned_work_center_id",
        help="The synthetic Unassigned card of this area.",
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)", "The work area code must be unique."),
    ]

    @api.constrains("model_ids")
    def _check_model_in_one_area(self):
        """A document has a single station, so a model may only be divided by
        one area: two areas would compete for the same field and both would
        count the same documents on their Unassigned card."""
        for area in self:
            clash = self.sudo().search(
                [("id", "!=", area.id), ("model_ids", "in", area.model_ids.ids)],
                limit=1,
            )
            if clash:
                shared = clash.model_ids & area.model_ids
                raise ValidationError(
                    _("%(model)s already belongs to work area %(area)s.")
                    % {"model": shared[0].name, "area": clash.name}
                )

    def _compute_unassigned_work_center_id(self):
        WorkCenter = self.env["work.center"].sudo().with_context(active_test=False)
        for area in self:
            area.unassigned_work_center_id = WorkCenter.search(
                [("area_id", "=", area.id), ("is_unassigned", "=", True)], limit=1
            )

    def _unassigned_name(self):
        """The card's name in the language of ``self``'s context."""
        return _("Unassigned")

    @api.model_create_multi
    def create(self, vals_list):
        areas = super().create(vals_list)
        # The card belongs to the area, not to a company: without a company it
        # stays visible under the multi-company record rule.
        cards = (
            self.env["work.center"]
            .sudo()
            .create(
                [
                    {
                        "name": self._unassigned_name(),
                        "area_id": area.id,
                        "is_unassigned": True,
                        "sequence": 0,
                        "company_id": False,
                    }
                    for area in areas
                ]
            )
        )
        # The card is created in code, so no .po reference can translate it;
        # fill every installed language in by hand.
        translations = {
            code: self.with_context(lang=code)._unassigned_name()
            for code, _name in self.env["res.lang"].get_installed()
        }
        for card in cards:
            card.update_field_translations("name", translations)
        return areas

    def unlink(self):
        WorkCenter = self.env["work.center"].sudo().with_context(active_test=False)
        used = WorkCenter.search(
            [("area_id", "in", self.ids), ("is_unassigned", "=", False)], limit=1
        )
        if used:
            raise UserError(
                _("Work area %(area)s still has stations; delete them first.")
                % {"area": used.area_id.name}
            )
        WorkCenter.with_context(work_center_area_unlink=True).search(
            [("area_id", "in", self.ids), ("is_unassigned", "=", True)]
        ).unlink()
        return super().unlink()
