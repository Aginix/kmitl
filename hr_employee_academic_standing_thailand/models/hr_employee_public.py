from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    academic_standing_id = fields.Many2one(
        related="employee_id.academic_standing_id",
        readonly=True,
    )
    rank_id = fields.Many2one(
        related="employee_id.rank_id",
        readonly=True,
    )
    rank_nobility_id = fields.Many2one(
        related="employee_id.rank_nobility_id",
        readonly=True,
    )
    profession_id = fields.Many2one(
        related="employee_id.profession_id",
        readonly=True,
    )

    academic_standing_title = fields.Char(
        related="employee_id.academic_standing_title",
        readonly=True,
    )
    academic_standing_title_abbreviation = fields.Char(
        related="employee_id.academic_standing_title_abbreviation",
        readonly=True,
    )
    academic_standing_title_en = fields.Char(
        related="employee_id.academic_standing_title_en",
        readonly=True,
    )
    academic_standing_title_abbreviation_en = fields.Char(
        related="employee_id.academic_standing_title_abbreviation_en",
        readonly=True,
    )
