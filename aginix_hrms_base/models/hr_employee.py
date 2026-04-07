from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    master_department_id = fields.Many2one(
        string="Master Department",
        comodel_name="hr.department",
        compute="_compute_master_department_id",
        store=True,
    )
    member_of_master_department = fields.Boolean(
        "Member of master department",
        compute="_compute_part_of_master_department",
        search="_search_part_of_master_department",
        help="Whether the employee is a member of the active user's department or one of it's child department.",
    )

    @api.depends("department_id")
    def _compute_master_department_id(self):
        for record in self:
            department = record.department_id
            if department:
                record.master_department_id = int(department.parent_path.split("/")[0])
            else:
                record.master_department_id = False
        self.clear_caches()

    @api.depends_context("uid", "company")
    @api.depends("department_id")
    def _compute_part_of_master_department(self):
        user_employee = self._get_valid_employee_for_user()
        active_department = user_employee.department_id
        if not active_department:
            self.member_of_master_department = False
        else:

            def get_master(department):
                parent = department.parent_id
                if not parent:
                    return self.env["hr.department"]
                return get_master(parent)

            master_departments = get_master(active_department)
            for employee in self:
                employee.member_of_master_department = (
                    employee.department_id == master_departments
                )

    def _search_part_of_master_department(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError(_("Operation not supported"))

        user_employee = self._get_valid_employee_for_user()

        # Double negation
        if not value:
            operator = "!=" if operator == "=" else "="
        if not user_employee.department_id:
            return [("id", operator, user_employee.id)]
        return (["!"] if operator == "!=" else []) + [
            ("master_department_id", "=", user_employee.master_department_id.id)
        ]
