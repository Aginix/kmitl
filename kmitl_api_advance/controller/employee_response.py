from odoo import http

from .api_key_jwt import ApiKeyJWT


class EmployeeResponse:
    def __init__(self, employee, api_key):
        self.__employee_service = EmployeeService(employee, api_key)

    def to_json(self):
        return {
            "email": self.__employee_service.get_email(),
            "prefix_th": self.__employee_service.get_prefix_th(),
            "first_name_th": self.__employee_service.get_first_name_th(),
            "last_name_th": self.__employee_service.get_last_name_th(),
            "job_title": self.__employee_service.get_job_title(),
            "code": self.__employee_service.get_kmitl_code(),
            "old_code": self.__employee_service.get_old_code(),
            "master_department_id": self.__employee_service.get_master_department_id(),
            "master_department_code": self.__employee_service.get_master_department_code(),
            "master_department": self.__employee_service.get_master_department(),
            "sub_department_id": self.__employee_service.get_sub_department_id(),
            "sub_department_code": self.__employee_service.get_sub_department_code(),
            "sub_department": self.__employee_service.get_sub_department(),
            "active": self.__employee_service.get_active(),
            "signature": self.__employee_service.get_signature(),
            "role": self.__employee_service.get_role(),
            "type": self.__employee_service.get_type(),
        }


class EmployeeService:
    def __init__(self, model, api_key=None):
        self.__employee_jwt = ApiKeyJWT()
        self.__api_key = api_key
        self.model = model

        self.prefix_th = (
            http.request.env["hr.employee.prefix"].with_context(lang="th_TH").search([])
        )

        self.employee_type = (
            http.request.env["hr.employee"]
            ._fields["kmitl_employee_type"]
            ._description_selection(http.request.env)
        )

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

    def get_job_title(self):
        return self.__get_data(self.model, "job_id.name")

    def get_master_department_id(self):
        department = self.__get_data(self.model, "department_id")

        if department:
            if department.parent_id:
                return self.__get_data(department, "parent_id.id")
            return self.__get_data(department, "id")
        return None

    def get_master_department_code(self):
        department = self.__get_data(self.model, "department_id")

        if department:
            if department.parent_id:
                return self.__get_data(department, "parent_id.code")
            return self.__get_data(department, "code")
        return None

    def get_master_department(self):
        department = self.__get_data(self.model, "department_id")

        if department:
            if department.parent_id:
                return self.__get_data(department, "parent_id.name")
            return self.__get_data(department, "name")
        return None

    def get_kmitl_code(self):
        return self.__get_data(self.model, "code")

    def get_old_code(self):
        return self.__get_data(self.model, "old_code")

    def get_active(self):
        return self.__get_data(self.model, "active", "boolean")

    def get_signature(self):
        signature = self.__get_data(self.model, "signature")

        if signature:
            return self.__employee_jwt.image_url_with_jwt(
                self.__api_key, self.model, "signature"
            )
        return None

    def get_sub_department_id(self):
        department = self.__get_data(self.model, "department_id")

        if department and department.parent_id:
            return self.__get_data(department, "id")
        return None

    def get_sub_department_code(self):
        department = self.__get_data(self.model, "department_id")

        if department and department.parent_id:
            return self.__get_data(department, "code")
        return None

    def get_sub_department(self):
        department = self.__get_data(self.model, "department_id")

        if department and department.parent_id:
            return self.__get_data(department, "name")
        return None

    def get_role(self):
        role_list = {
            "academic": "สายวิชาการ",
            "support": "สายสนับสนุนวิชาการ",
        }

        role = self.__get_data(self.model, "role")

        if role:
            return role_list[role]
        return None

    def get_type(self):
        emp_type = self.__get_data(self.model, "kmitl_employee_type")
        return dict(self.employee_type)[emp_type] if emp_type else None

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

    def __get_data_array(self, obj, attr, subattr):
        objs = getattr(obj, attr)

        if len(objs) == 0:
            return None

        tmp_data = []

        for item in objs:
            tmp_item = {}
            for key, attr in subattr:
                tmp_item[key] = self.__get_data(item, attr)
            tmp_data.append(tmp_item)
        return tmp_data
