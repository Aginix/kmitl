from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # Override the manually-set flag from the base module so that "ดร."/"Dr." is
    # derived automatically from the employee's highest education level.
    title_dr = fields.Boolean(
        compute="_compute_title_dr",
        store=True,
        readonly=True,
    )

    @api.depends("education_level_id")
    def _compute_title_dr(self):
        dr_education = self.env.ref(
            "hr_employee_education_history.Q01", raise_if_not_found=False
        )
        for rec in self:
            rec.title_dr = bool(dr_education and dr_education == rec.education_level_id)
