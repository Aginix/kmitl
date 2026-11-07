from odoo import models

from ..utils import jwt_helper
from ..utils.model_helper import get_value


class ApiBaseHrEmployeeServiceKmitl(models.AbstractModel):
    _name = "api.base.hr.employee.service.kmitl"
    _description = "Employee Service for API Base"

    def _get_role(self, employee_role):
        role_selections = dict(
            self.env["hr.employee"]
            .with_context(lang="th_TH")
            .fields_get(["role"])["role"]["selection"]
        )

        if employee_role:
            return role_selections[employee_role]
        else:
            return None

    def _get_master_department(self, department):
        if department:
            return get_value(department.master_department_id, "name")
        return None

    def _get_manager(self, manager):
        if manager:
            return {
                "kid": get_value(manager, "kid"),
                "kmitl_code": get_value(manager, "code"),
                "email": get_value(manager, "work_email"),
                "first_name_th": get_value(manager, "firstname"),
                "middle_name_th": get_value(manager, "middlename"),
                "last_name_th": get_value(manager, "lastname"),
                "first_name_en": get_value(manager, "firstname_secondary"),
                "middle_name_en": get_value(manager, "middlename_secondary"),
                "last_name_en": get_value(manager, "lastname_secondary"),
                "old_code": get_value(manager, "old_code"),
            }
        return None

    def _get_position_level(self, position_level):
        def _get_discipline(discipline):
            if discipline:
                return {
                    "code": get_value(discipline, "code"),
                    "name": get_value(discipline, "name"),
                }
            return None

        if position_level:
            return {
                "name": get_value(position_level.relation_id, "name"),
                "effective_date": get_value(position_level, "effective_date"),
                "discipline": _get_discipline(position_level.discipline_id),
                "subdiscipline": _get_discipline(position_level.subdiscipline_id),
                "order_no": get_value(position_level.office_order_id, "ref_no"),
                "order_date": get_value(position_level, "order_date"),
            }
        return None

    def get_employees_count(self):
        employees = (
            self.env["hr.employee"]
            .with_context(active_test=False)
            .search_count([("code", "!=", "")])
        )
        return employees

    def get_employees(self, limit=10, offset=0):
        employees = (
            self.env["hr.employee"]
            .with_context(lang="th_TH", active_test=False)
            .search([("code", "!=", "")], limit=limit, offset=offset, order="code")
        )
        return [
            {
                "active": get_value(emp, "active", value_type=bool),
                "kmitl_code": get_value(emp, "code"),
                "email": get_value(emp, "work_email"),
                "prefix_en": get_value(emp.prefix_id, "name", "en_US"),
                "prefix_th": get_value(emp.prefix_id, "name"),
                "first_name_en": get_value(emp, "firstname_secondary"),
                "first_name_th": get_value(emp, "firstname"),
                "middle_name_en": get_value(emp, "middlename_secondary"),
                "middle_name_th": get_value(emp, "middlename"),
                "last_name_en": get_value(emp, "lastname_secondary"),
                "last_name_th": get_value(emp, "lastname"),
                "full_name_en": get_value(emp, "name_secondary"),
                "full_name_th": get_value(emp, "name"),
                "service_start_date": get_value(emp, "service_start_date"),
                "type": get_value(emp, "kmitl_employee_type"),
                "role": self._get_role(emp.role),
                "position_level": self._get_position_level(emp.position_level_id),
                "job_title": get_value(emp.job_id, "name"),
                "master_department": self._get_master_department(emp.department_id),
                "sub_department": get_value(emp.department_id, "name"),
                "master_original_department": self._get_master_department(
                    emp.original_department_id
                ),
                "sub_original_department": get_value(
                    emp.original_department_id, "name"
                ),
                "master_academic_department": self._get_master_department(
                    emp.academic_department_id
                ),
                "sub_academic_department": get_value(
                    emp.academic_department_id, "name"
                ),
                "kid": get_value(emp, "kid"),
                "manager": self._get_manager(emp.parent_id),
                "old_code": get_value(emp, "old_code"),
                "academic_standing_title": get_value(emp, "academic_standing_title"),
                "academic_standing_title_abbreviation": get_value(
                    emp, "academic_standing_title_abbreviation"
                ),
                "academic_standing_title_en": get_value(
                    emp, "academic_standing_title_en"
                ),
                "academic_standing_title_abbreviation_en": get_value(
                    emp, "academic_standing_title_abbreviation_en"
                ),
                "last_update": get_value(emp, "write_date"),
                "image_url": "/api/base/v1/employees/{employee_id}/image?token={token}".format(
                    employee_id=emp.id,
                    token=jwt_helper.generate_jwt(emp.id, expires_in=5 * 60),
                ),
            }
            for emp in employees
        ]

    def get_employee_by_identifier(self, identifier):
        employee = (
            self.env["hr.employee"]
            .with_context(lang="th_TH", active_test=False)
            .search(
                [
                    "|",
                    "|",
                    ("code", "=", identifier),
                    ("work_email", "=", identifier),
                    ("kid", "=", identifier),
                ],
                limit=1,
            )
        )

        return (
            {
                "active": get_value(employee, "active", value_type=bool),
                "kmitl_code": get_value(employee, "code"),
                "email": get_value(employee, "work_email"),
                "prefix_en": get_value(employee.prefix_id, "name", "en_US"),
                "prefix_th": get_value(employee.prefix_id, "name"),
                "first_name_en": get_value(employee, "firstname_secondary"),
                "first_name_th": get_value(employee, "firstname"),
                "middle_name_en": get_value(employee, "middlename_secondary"),
                "middle_name_th": get_value(employee, "middlename"),
                "last_name_en": get_value(employee, "lastname_secondary"),
                "last_name_th": get_value(employee, "lastname"),
                "full_name_en": get_value(employee, "name_secondary"),
                "full_name_th": get_value(employee, "name"),
                "service_start_date": get_value(employee, "service_start_date"),
                "type": get_value(employee, "kmitl_employee_type"),
                "role": self._get_role(employee.role),
                "position_level": self._get_position_level(employee.position_level_id),
                "job_title": get_value(employee.job_id, "name"),
                "master_department": self._get_master_department(
                    employee.department_id
                ),
                "sub_department": get_value(employee.department_id, "name"),
                "master_original_department": self._get_master_department(
                    employee.original_department_id
                ),
                "sub_original_department": get_value(
                    employee.original_department_id, "name"
                ),
                "master_academic_department": self._get_master_department(
                    employee.academic_department_id
                ),
                "sub_academic_department": get_value(
                    employee.academic_department_id, "name"
                ),
                "kid": get_value(employee, "kid"),
                "manager": self._get_manager(employee.parent_id),
                "old_code": get_value(employee, "old_code"),
                "academic_standing_title": get_value(
                    employee, "academic_standing_title"
                ),
                "academic_standing_title_abbreviation": get_value(
                    employee, "academic_standing_title_abbreviation"
                ),
                "academic_standing_title_en": get_value(
                    employee, "academic_standing_title_en"
                ),
                "academic_standing_title_abbreviation_en": get_value(
                    employee, "academic_standing_title_abbreviation_en"
                ),
                "last_update": get_value(employee, "write_date"),
                "image_url": "/api/base/v1/employees/{employee_id}/image?token={token}".format(
                    employee_id=employee.id,
                    token=jwt_helper.generate_jwt(employee.id, expires_in=5 * 60),
                ),
            }
            if employee
            else None
        )
