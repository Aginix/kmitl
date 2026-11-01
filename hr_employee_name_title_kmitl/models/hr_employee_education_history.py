from odoo import api, models


class HrEmployeeEducationHistory(models.Model):
    _inherit = "hr.employee.education.history"

    # The employee's education_level_id (and thus the "ดร." in academic_standing_title)
    # is computed from these education-history lines. Changing a line does not write
    # education_level_id into the employee's vals, so the employee's name sync would be
    # missed. Re-sync the owning employee's name whenever a line is added, removed, or
    # its level changes.
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.employee_id._sync_name_title()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "education_level_id" in vals or "employee_id" in vals:
            self.employee_id._sync_name_title()
        return res

    def unlink(self):
        employees = self.employee_id
        res = super().unlink()
        employees._sync_name_title()
        return res
