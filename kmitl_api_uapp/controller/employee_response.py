class EmployeeResponse:
    def __init__(self, employee):
        self.__employee_service = EmployeeService(employee)

    def to_json(self):
        return {
            "id": self.__employee_service.get_id(),
            "code": self.__employee_service.get_kmitl_code(),
            "type": self.__employee_service.get_type(),
            "degree": self.__employee_service.get_degree(),
            "prefix_en": self.__employee_service.get_prefix_en(),
            "first_name_en": self.__employee_service.get_first_name_en(),
            "last_name_en": self.__employee_service.get_last_name_en(),
            "prefix_th": self.__employee_service.get_prefix_th(),
            "first_name_th": self.__employee_service.get_first_name_th(),
            "last_name_th": self.__employee_service.get_last_name_th(),
            "gender": self.__employee_service.get_gender(),
            "master_department_id": self.__employee_service.get_master_department_id(),
            "master_department_name_th": self.__employee_service.get_master_department_name_th(),
            "master_department_name_en": self.__employee_service.get_master_department_name_en(),
            "department_id": self.__employee_service.get_department_id(),
            "department_name_th": self.__employee_service.get_department_name_th(),
            "department_name_en": self.__employee_service.get_department_name_en(),
            "work_email": self.__employee_service.get_email(),
            "active": self.__employee_service.get_active(),
            "nationality": self.__employee_service.get_nationality(),
            "last_updated_at": self.__employee_service.get_last_updated_at(),
            "citizen_id": self.__employee_service.get_citizen_id(),
            "passport_id": self.__employee_service.get_passport_id(),
            "username": self.__employee_service.get_username(),
        }


class EmployeeService:
    def __init__(self, model):
        self.model = model

    def get_username(self):
        email = self.__get_data(self.model, "work_email")
        username = email.split("@")[0]
        return username

    def get_active(self):
        return self.__get_data(self.model, "active", "boolean")

    def get_last_updated_at(self):
        return self.__get_data(self.model, "write_date")

    def get_nationality(self):
        return self.__get_data(self.model, "country_id.name")

    def get_citizen_id(self):
        return self.__get_data(self.model, "identification_id")

    def get_passport_id(self):
        return self.__get_data(self.model, "passport_id")

    def get_id(self):
        return self.__get_data(self.model, "id")

    def get_email(self):
        return self.__get_data(self.model, "work_email")

    def get_gender(self):
        return self.__get_data(self.model, "gender")

    def get_prefix_th(self):
        prefix = self.__get_data(self.model, "prefix_id")

        return self.__get_data(prefix.with_context(lang="th_TH"), "name")

    def get_first_name_th(self):
        return self.__get_data(self.model, "firstname")

    def get_last_name_th(self):
        return self.__get_data(self.model, "lastname")

    def get_prefix_en(self):
        prefix = self.__get_data(self.model, "prefix_id")

        return self.__get_data(prefix.with_context(lang="en_US"), "name")

    def get_first_name_en(self):
        return self.__get_data(self.model, "firstname_secondary")

    def get_last_name_en(self):
        return self.__get_data(self.model, "lastname_secondary")

    def get_job_title(self):
        return self.__get_data(self.model, "job_id.name")

    def get_master_department_id(self):
        department = self.__get_data(self.model, "department_id")

        if not department:
            return None

        return self.__get_data(department, "master_department_id.id")

    def get_master_department_name_th(self):
        department = self.__get_data(self.model, "department_id")

        if not department:
            return None

        return self.__get_data(department, "master_department_id.name")

    def get_master_department_name_en(self):
        department = self.__get_data(self.model, "department_id")

        if not department:
            return None
        return self.__get_data(department, "master_department_id.name_secondary")

    def get_department_id(self):
        department = self.__get_data(self.model, "department_id")

        if not department:
            return None

        return self.__get_data(department, "id")

    def get_department_name_th(self):
        department = self.__get_data(self.model, "department_id")

        if not department:
            return None

        return self.__get_data(department, "name")

    def get_department_name_en(self):
        department = self.__get_data(self.model, "department_id")

        if not department:
            return None
        return self.__get_data(department, "name_secondary")

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
                if getattr(tmp_obj, value) is False:
                    return None
                return getattr(tmp_obj, value)
            tmp_obj = getattr(tmp_obj, value)

    def get_type(self):
        return self.__get_data(self.model, "role")

    def get_degree(self):
        educations = self.__get_data(self.model, "education_history_ids")

        sorted_educations = educations.sorted(
            key=lambda x: x.education_level_id.level, reverse=True
        )

        if not sorted_educations:
            return None

        return self.__get_data(sorted_educations[0], "education_level_id.name")
