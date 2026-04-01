from datetime import datetime

from odoo import api, fields, models


class HrEmployeeEducationHistory(models.Model):
    _name = "hr.employee.education.history"
    _description = "HR Employee Education History"
    _order = "graduation_year desc"

    employee_id = fields.Many2one(comodel_name="hr.employee", required=True)
    university_id = fields.Many2one(
        comodel_name="resource.university", string="University"
    )
    education_level_id = fields.Many2one(
        comodel_name="resource.education.level", string="Education Level"
    )
    faculty_id = fields.Many2one(
        comodel_name="resource.education.faculty", string="Faculty"
    )
    department_id = fields.Many2one(
        comodel_name="resource.education.department", string="Department"
    )
    program_id = fields.Many2one(
        comodel_name="resource.education.program", string="Program"
    )
    start_year = fields.Selection(selection="year_selection")
    graduation_year = fields.Selection(selection="year_selection")
    country = fields.Char(string="Country", related="university_id.country_id.name")
    university_name = fields.Char(
        string="University Name", related="university_id.name"
    )
    university_name_th = fields.Char(
        string="University Name (Thai)", related="university_id.name_th"
    )

    def name_get(self):
        return [
            (
                record.id,
                f"{record.employee_id.name} - {record.education_level_id.name}",
            )
            for record in self
        ]

    @api.model
    def year_selection(self):
        end_year = datetime.now().year + 5
        year = 1900
        year_list = []
        while year != end_year:
            year_list.append((str(year), f"{str(year)} ({str(year+543)})"))
            year += 1
        return year_list
