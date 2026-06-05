from odoo import _, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def name_get(self):
        """Append academic standing, email, department and KID as extra lines
        when the ``show_employee_detail`` context flag is set.

        The Many2OneField widget splits ``display_name`` on newlines: the first
        line is the displayed value, the rest are rendered as muted extra lines
        below the input (same mechanism as the partner ``show_address`` flag).
        Use together with ``options="{'always_reload': True}"`` on the field so
        ``name_get`` is re-evaluated with the field context.
        """
        res = super().name_get()
        if not self.env.context.get("show_employee_detail"):
            return res
        names = dict(res)
        result = []
        for employee in self:
            lines = [names.get(employee.id, "")]
            if employee.academic_standing_title:
                lines.append(employee.academic_standing_title)
            if employee.work_email:
                lines.append(employee.work_email)
            if employee.department_id:
                lines.append(employee.department_id.complete_name)
            if employee.kid and employee.kid != _("New"):
                lines.append("KID: %s" % employee.kid)
            result.append((employee.id, "\n".join(lines)))
        return result
