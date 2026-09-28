from odoo import models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"
    _rec_names_search = ["name", "academic_standing_name_search"]

    def name_get(self):
        """Prefix the abbreviated academic standing title to the employee name
        (e.g. "รศ. ดร. ปานวิทย์ ธุวะนุติ") so search results and pickers show the
        title in front of the name. Shared by hr.employee and
        hr.employee.public."""
        res = super().name_get()
        names = dict(res)
        result = []
        for employee in self:
            name = names.get(employee.id) or employee.name or ""
            abbreviation = employee.academic_standing_title_abbreviation
            if abbreviation:
                name = "{abbreviation} {name}".format(
                    abbreviation=abbreviation, name=name
                ).strip()
            result.append((employee.id, name))
        return result
