from odoo import http
from .api_key_jwt import ApiKeyJWT


class EmployeeResponse:
    def __init__(self, employee, api_key):
        self.__employee_service = EmployeeService(employee, api_key)

    def to_json(self):
        return {
            "id": self.__employee_service.get_id(),
            "email": self.__employee_service.get_email(),
            "prefix_th": self.__employee_service.get_prefix_th(),
            "first_name_th": self.__employee_service.get_first_name_th(),
            "last_name_th": self.__employee_service.get_last_name_th(),
            "prefix_en": self.__employee_service.get_prefix_en(),
            "first_name_en": self.__employee_service.get_first_name_en(),
            "last_name_en": self.__employee_service.get_last_name_en(),
            "job_title": self.__employee_service.get_job_title(),
            "code": self.__employee_service.get_kmitl_code(),
            "master_department_id": self.__employee_service.get_master_department_id(),
            "master_department": self.__employee_service.get_master_department(),
            "sub_department": self.__employee_service.get_sub_department(),
            "role": self.__employee_service.get_role(),
        }


class EmployeeService:
    def __init__(self, model, api_key=None):
        self.__employee_jwt = ApiKeyJWT()
        self.__api_key = api_key
        self.model = model

        self.prefix_th = (
            http.request.env["hr.employee.prefix"].with_context(lang="th_TH").search([])
        )
        self.prefix_en = (
            http.request.env["hr.employee.prefix"].with_context(lang="en_US").search([])
        )

    def get_id(self):
        return self.__get_data(self.model, "id")

    def get_email(self):
        return self.__get_data(self.model, "work_email")

    def get_prefix_th(self):
        prefix = self.__get_data(self.model, "prefix_id.id")

        if not prefix:
            return None

        return list(filter(lambda p: p.id == prefix, self.prefix_th))[0].name

    def get_first_name_th(self):
        return self.__get_data(self.model, "firstname")

    def get_last_name_th(self):
        return self.__get_data(self.model, "lastname")

    def get_prefix_en(self):
        prefix = self.__get_data(self.model, "prefix_id.id")

        if not prefix:
            return None

        return list(filter(lambda p: p.id == prefix, self.prefix_en))[0].name

    def get_first_name_en(self):
        return self.__get_data(self.model, "firstname_secondary")

    def get_last_name_en(self):
        return self.__get_data(self.model, "lastname_secondary")

    def get_job_title(self):
        return self.__get_data(self.model, "job_id.name")

    def get_master_department_id(self):
        department = self.__get_data(self.model, "department_id")

        if department.parent_id:
            return department.parent_id.id
        return self.__get_data(department, "id")

    def get_master_department(self):
        department = self.__get_data(self.model, "department_id")

        if department.parent_id:
            return department.parent_id.name
        return self.__get_data(department, "name")

    def get_sub_department(self):
        department = self.__get_data(self.model, "department_id")

        if department.parent_id:
            return department.name
        return None

    def get_kmitl_code(self):
        return self.__get_data(self.model, "code")

    def get_old_code(self):
        return self.__get_data(self.model, "old_code")

    def get_employment_status(self):
        return self.__get_data(self.model, "employment_status")

    def get_role(self):
        role_list = {
            "academic": "สายวิชาการ",
            "support": "สายสนับสนุนวิชาการ",
        }

        role = self.__get_data(self.model, "role")

        if role:
            return role_list[role]
        return None

    def __get_data(self, obj, attr, data_type=None):
        list_attr = attr.split(".")
        tmp_obj = obj
        for index, value in enumerate(list_attr):
            if index == len(list_attr) - 1:
                if data_type == "boolean":
                    return getattr(tmp_obj, value)
                if not getattr(tmp_obj, value):
                    return None
                return getattr(tmp_obj, value)
            tmp_obj = getattr(tmp_obj, value)
