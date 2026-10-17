from ..utils.model_helper import get_value


class HrEmployeePrivateContactService:
    def __init__(self, request):
        self.env = request.env

    def get_private_contact(self, identifier):
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

        return {
            "address_home_street": get_value(employee, "address_home_street"),
            "address_home_street2": get_value(employee, "address_home_street2"),
            "address_home_city": get_value(employee, "address_home_city"),
            "address_home_state": get_value(employee.address_home_state_id, "name"),
            "address_home_country": get_value(employee.address_home_country_id, "name"),
            "address_home_zip": get_value(employee, "address_home_zip"),
            "current_home_street": get_value(employee, "current_home_street"),
            "current_home_street2": get_value(employee, "current_home_street2"),
            "current_home_city": get_value(employee, "current_home_city"),
            "current_home_state": get_value(employee.current_home_state_id, "name"),
            "current_home_country": get_value(employee.current_home_country_id, "name"),
            "current_home_zip": get_value(employee, "current_home_zip"),
            "private_email": get_value(employee, "private_email"),
            "phone": get_value(employee, "phone"),
            "marital": get_value(employee, "marital"),
            "emergency_contact": get_value(employee, "emergency_contact"),
            "emergency_phone": get_value(employee, "emergency_phone"),
        }
