from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    education_history_ids = fields.One2many(
        comodel_name="hr.employee.education.history",
        inverse_name="employee_id",
    )

    education_level_id = fields.Many2one(
        string="Education Level",
        comodel_name="resource.education.level",
        compute="_compute_highest_education_id",
        store=True,
        readonly=True,
    )

    def _get_highest_education(self):
        self.ensure_one()
        education_levels = self.sudo().education_history_ids
        if len(education_levels) == 0:
            return False
        return max(education_levels, key=lambda x: x.education_level_id.level)

    @api.depends("education_history_ids")
    def _compute_highest_education_id(self):
        for record in self:
            highest_level = record._get_highest_education()
            if highest_level:
                record.education_level_id = highest_level.education_level_id.id
            else:
                record.education_level_id = False
