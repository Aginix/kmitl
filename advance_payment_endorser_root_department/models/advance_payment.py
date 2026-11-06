from odoo import models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    def _compute_endorser_id(self):
        """Suggest the manager of the borrower's top-level unit (คณะ/สำนัก)
        instead of the line manager. Still a suggestion: it stays
        overridable (ADR-0020)."""
        super()._compute_endorser_id()
        for rec in self.filtered(lambda r: r.state == "draft"):
            rec.endorser_id = rec._get_root_department_endorser()

    def _get_root_department_endorser(self):
        """The root unit's manager; the line manager when the borrower is
        that manager; nobody when the unit has none (submit then blocks)."""
        self.ensure_one()
        employee = self.employee_id.sudo()
        department = employee.department_id
        if not department:
            return employee.parent_id.user_id
        root = department.browse(int(department.parent_path.split("/")[0]))
        manager = root.manager_id
        if manager == employee:
            return employee.parent_id.user_id
        return manager.user_id
