from odoo import api, models, fields


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    position_level_ids = fields.One2many(
        comodel_name="hr.employee.position.level",
        inverse_name="employee_id",
    )

    position_level_id = fields.Many2one(
        comodel_name="hr.employee.position.level",
        compute="_compute_position_level_id",
        store=True,
        readonly=True,
    )

    position_level_relation_id = fields.Many2one(
        comodel_name="hr.employee.position.level.relation",
        compute="_compute_position_level_relation_id",
        store=True,
        readonly=True,
    )

    position_level = fields.Char(
        related="position_level_id.relation_id.name",
        readonly=True,
        store=False,
    )

    def _get_highest_position_level(self):
        self.ensure_one()
        position_levels = self.sudo().position_level_ids
        if len(position_levels) == 0:
            return False
        return max(position_levels, key=lambda x: x.level)

    @api.depends("position_level_ids")
    def _compute_position_level_id(self):
        for record in self:
            highest_level = record._get_highest_position_level()
            if highest_level:
                record.position_level_id = highest_level.id
            else:
                record.position_level_id = False

    @api.depends("position_level_ids")
    def _compute_position_level_relation_id(self):
        for record in self:
            highest_level = record._get_highest_position_level()
            if highest_level:
                record.position_level_relation_id = highest_level.relation_id
            else:
                record.position_level_relation_id = False
