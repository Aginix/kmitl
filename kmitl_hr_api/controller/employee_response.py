from odoo import http

from .api_key_jwt import ApiKeyJWT
from .utils import get_data


class EmployeeResponse:
    def __init__(self, employee, api_key):
        self.__employee_service = EmployeeService(employee, api_key)

    def to_json(self):
        return {
            "active": self.__employee_service.get_active(),
            "blood_group": self.__employee_service.get_blood_group(),
            "change_status_to_university_staff": self.__employee_service.get_change_status_to_university_staff(),
            "citizen_id": self.__employee_service.get_citizen_id(),
            "country": self.__employee_service.get_country(),
            "date_of_birth": self.__employee_service.get_date_of_birth(),
            "email": self.__employee_service.get_email(),
            "first_contract_date": self.__employee_service.get_first_contract_date(),
            "first_name_en": self.__employee_service.get_first_name_en(),
            "first_name_th": self.__employee_service.get_first_name_th(),
            "full_name_en": self.__employee_service.get_full_name_en(),
            "full_name_th": self.__employee_service.get_full_name_th(),
            "id": self.__employee_service.get_id(),
            "image": self.__employee_service.get_image(),
            "image_thumbnail": self.__employee_service.get_image_thumbnail(),
            "job_title": self.__employee_service.get_job_title(),
            "kmitl_code": self.__employee_service.get_kmitl_code(),
            "last_name_en": self.__employee_service.get_last_name_en(),
            "last_name_th": self.__employee_service.get_last_name_th(),
            "management_positions": self.__employee_service.get_management_positions(),
            "middle_name_en": self.__employee_service.get_middle_name_en(),
            "middle_name_th": self.__employee_service.get_middle_name_th(),
            "master_department": self.__employee_service.get_master_department(),
            "old_code": self.__employee_service.get_old_code(),
            "passport_no": self.__employee_service.get_passport_no(),
            "position_level": self.__employee_service.get_position_level(),
            "prefix_en": self.__employee_service.get_prefix_en(),
            "prefix_th": self.__employee_service.get_prefix_th(),
            "role": self.__employee_service.get_role(),
            "service_start_date": self.__employee_service.get_service_start_date(),
            "sub_department": self.__employee_service.get_sub_department(),
            "type": self.__employee_service.get_type(),
            "departure_date": self.__employee_service.get_departure_date(),
            "departure_description": self.__employee_service.get_departure_description(),
            "departure_office_order_ref_no": self.__employee_service.get_departure_office_order_ref_no(),
            "departure_type": self.__employee_service.get_departure_type(),
            "welfare_type": self.__employee_service.get_welfare_type(),
            "signature": self.__employee_service.get_signature(),
            "kid": self.__employee_service.get_kid(),
            "master_academic_department": self.__employee_service.get_master_academic_department(),
            "sub_academic_department": self.__employee_service.get_sub_academic_department(),
            "manager": self.__employee_service.get_manager(),
            "last_update": self.__employee_service.get_last_update(),
        }


class EmployeeService:
    def __init__(self, model, api_key=None):
        self.model = model
        self.__api_key = api_key
        self.__employee_jwt = ApiKeyJWT()

        self.employee_type = (
            http.request.env["hr.employee"]
            ._fields["kmitl_employee_type"]
            ._description_selection(http.request.env)
        )

    def get_active(self):
        return get_data(self.model, "active", "boolean")

    def get_address_home_street(self):
        return get_data(self.model, "address_home_street")

    def get_address_home_street2(self):
        return get_data(self.model, "address_home_street2")

    def get_address_home_city(self):
        return get_data(self.model, "address_home_city")

    def get_address_home_state(self):
        address_home_state_id = get_data(self.model, "address_home_state_id")
        return address_home_state_id.name if address_home_state_id else None

    def get_address_home_country(self):
        address_home_country_id = get_data(self.model, "address_home_country_id")
        return address_home_country_id.name if address_home_country_id else None

    def get_address_home_zip(self):
        return get_data(self.model, "address_home_zip")

    def get_relatives(self):
        return get_data(self.model, "relative_ids")

    def get_contracts(self):
        return get_data(self.model, "contract_ids")

    def get_blood_group(self) -> str:
        return get_data(self.model, "blood_group")

    def get_change_status_to_university_staff(self):
        for i in self.model.movement_ids:
            if i.movement_type_id.id == 14:
                return (
                    {
                        "effective_date": i.effective_date,
                    },
                )
        return None

    def get_citizen_id(self):
        return get_data(self.model, "identification_id")

    def get_country(self):
        country = get_data(self.model, "country_id")

        if not country:
            return None

        return country.name

    def get_current_home_street(self):
        return get_data(self.model, "current_home_street")

    def get_current_home_street2(self):
        return get_data(self.model, "current_home_street2")

    def get_current_home_city(self):
        return get_data(self.model, "current_home_city")

    def get_current_home_state(self):
        current_home_state_id = get_data(self.model, "current_home_state_id")
        return current_home_state_id.name if current_home_state_id else None

    def get_current_home_country(self):
        current_home_country_id = get_data(self.model, "current_home_country_id")
        return current_home_country_id.name if current_home_country_id else None

    def get_current_home_zip(self):
        return get_data(self.model, "current_home_zip")

    def get_date_of_birth(self):
        return get_data(self.model, "birthday")

    def get_departure_date(self):
        departure_date = get_data(self.model, "departure_date")

        if departure_date:
            return departure_date
        return None

    def get_departure_description(self):
        departure_description = get_data(self.model, "departure_description")

        if departure_description:
            return departure_description
        return None

    def get_departure_office_order_ref_no(self):
        departure_office_order_id = get_data(self.model, "departure_office_order_id")

        if departure_office_order_id:
            return departure_office_order_id.ref_no
        return None

    def get_departure_type(self):
        departure_reason_id = get_data(self.model, "departure_reason_id")

        if departure_reason_id:
            return departure_reason_id.name
        return None

    def get_email(self):
        return get_data(self.model, "work_email")

    def get_emergency_contact(self):
        return get_data(self.model, "emergency_contact")

    def get_emergency_phone(self):
        return get_data(self.model, "emergency_phone")

    def get_first_contract_date(self):
        return get_data(self.model, "first_contract_date")

    def get_first_name_en(self):
        return get_data(self.model, "firstname_secondary")

    def get_first_name_th(self):
        return get_data(self.model, "firstname")

    def get_full_name_en(self):
        return get_data(self.model, "name_secondary")

    def get_full_name_th(self):
        return get_data(self.model, "name")

    def get_id(self):
        return get_data(self.model, "id")

    def get_image(self):
        return self.__employee_jwt.image_url_with_jwt(
            self.__api_key, self.model, "image_1920"
        )

    def get_image_thumbnail(self):
        return self.__employee_jwt.image_url_with_jwt(
            self.__api_key, self.model, "image_1920"
        )

    def get_job_title(self):
        return get_data(self.model, "job_id.name")

    def get_kmitl_code(self):
        return get_data(self.model, "code")

    def get_last_name_en(self):
        return get_data(self.model, "lastname_secondary")

    def get_last_name_th(self):
        return get_data(self.model, "lastname")

    def get_management_positions(self):
        management_data = []
        managements = get_data(self.model, "management_record_ids")
        for i in managements:
            department = get_data(i, "department_id")

            master_department = department.name
            sub_department = None
            if department.parent_id:
                master_department = department.parent_id.name
                sub_department = department.name

            management_data.append(
                {
                    "id": get_data(i, "id"),
                    "name": get_data(i, "management_position_id.name"),
                    "division": get_data(i, "division"),
                    "master_department": master_department,
                    "sub_department": sub_department,
                    "start_date": get_data(i, "date_start"),
                    "end_date": get_data(i, "date_end"),
                    "order_no": get_data(i, "office_order_id.ref_no"),
                    "order_date": get_data(i, "order_date"),
                    "effective": get_data(i, "effective", "boolean"),
                }
            )

        return management_data

    def get_marital(self):
        return get_data(self.model, "marital")

    def get_master_department(self):
        department = get_data(self.model, "department_id")

        if department.parent_id:
            return department.parent_id.name
        return department.name

    def get_middle_name_en(self):
        return get_data(self.model, "middlename_secondary")

    def get_middle_name_th(self):
        return get_data(self.model, "middlename")

    def get_old_code(self):
        return get_data(self.model, "old_code")

    def get_passport_no(self):
        return get_data(self.model, "passport_id")

    def get_position_level(self):
        if get_data(self.model, "position_level_id.id"):
            discipline = None
            if get_data(self.model, "position_level_id.discipline_id.code"):
                discipline = {
                    "code": get_data(
                        self.model, "position_level_id.discipline_id.code"
                    ),
                    "name": get_data(
                        self.model, "position_level_id.discipline_id.name"
                    ),
                }

            subdiscipline = None
            if get_data(self.model, "position_level_id.subdiscipline_id.code"):
                subdiscipline = {
                    "code": get_data(
                        self.model, "position_level_id.subdiscipline_id.code"
                    ),
                    "name": get_data(
                        self.model, "position_level_id.subdiscipline_id.name"
                    ),
                }

            position = {
                "name": get_data(self.model, "position_level_id.relation_id.name"),
                "effective_date": get_data(
                    self.model, "position_level_id.effective_date"
                ),
                "discipline": discipline,
                "subdiscipline": subdiscipline,
                "order_no": get_data(
                    self.model, "position_level_id.office_order_id.ref_no"
                ),
                "order_date": get_data(self.model, "position_level_id.order_date"),
            }

            return position
        return None

    def get_prefix_en(self):
        prefix = get_data(self.model.with_context(lang="en_US"), "prefix_id")

        if not prefix:
            return None

        return prefix.name

    def get_prefix_th(self):
        prefix = get_data(self.model.with_context(lang="th_TH"), "prefix_id")

        if not prefix:
            return None

        return prefix.name

    def get_private_email(self):
        return get_data(self.model, "private_email")

    def get_phone(self):
        return get_data(self.model, "phone")

    def get_role(self):
        role_list = {
            "academic": "สายวิชาการ",
            "support": "สายสนับสนุนวิชาการ",
        }

        role = get_data(self.model, "role")

        if role:
            return role_list[role]
        return None

    def get_service_start_date(self):
        return get_data(self.model, "service_start_date")

    def get_sub_department(self):
        department = get_data(self.model, "department_id")

        if department.parent_id:
            return department.name
        return None

    def get_type(self):
        emp_type = get_data(self.model, "kmitl_employee_type")
        return dict(self.employee_type)[emp_type] if emp_type else None

    def get_welfare_type(self):
        welfare_type = get_data(self.model, "kmitl_welfare_type")
        return welfare_type

    def get_signature(self):
        signature = get_data(self.model, "signature")

        if signature:
            return self.__employee_jwt.image_url_with_jwt(
                self.__api_key, self.model, "signature"
            )
        return None

    def get_kid(self):
        return get_data(self.model, "kid")

    def get_master_academic_department(self):
        department = get_data(self.model, "academic_department_id")

        if department.parent_id:
            return get_data(department.parent_id, "name")
        return get_data(department, "name")

    def get_sub_academic_department(self):
        department = get_data(self.model, "academic_department_id")

        if department.parent_id:
            return department.name
        return None

    def get_manager(self):
        manager = get_data(self.model, "parent_id")

        if manager:
            return {
                "kid": get_data(manager, "kid"),
                "kmitl_code": get_data(manager, "code"),
                "email": get_data(manager, "work_email"),
                "first_name_th": get_data(manager, "firstname"),
                "middle_name_th": get_data(manager, "middlename"),
                "last_name_th": get_data(manager, "lastname"),
                "first_name_en": get_data(manager, "firstname_secondary"),
                "middle_name_en": get_data(manager, "middlename_secondary"),
                "last_name_en": get_data(manager, "lastname_secondary"),
            }
        return None

    def get_last_update(self):
        return get_data(self.model, "__last_update")
