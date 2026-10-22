from odoo import models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"
    # Keep the hidden search index so a bare title, bare name or "title + name"
    # all match. The display name itself no longer needs a prefix: the academic
    # standing title is now composed into ``name`` by hr_employee_name_title_kmitl,
    # so prepending the abbreviation here would double it.
    _rec_names_search = ["name", "academic_standing_name_search"]
