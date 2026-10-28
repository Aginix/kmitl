from ..utils.model_helper import get_value


class HrEmployeeRelativeService:
    def __init__(self, request):
        self.env = request.env

    def get_relatives(self, identifier):
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

        return [
            {
                "relation": get_value(relative.relation_id, "name"),
                "identification_id": get_value(relative, "identification_id"),
                "prefix": get_value(relative.prefix_id, "name"),
                "firstname": get_value(relative, "firstname"),
                "middlename": get_value(relative, "middlename"),
                "lastname": get_value(relative, "lastname"),
                "date_of_birth": get_value(relative, "date_of_birth"),
                "claim": get_value(relative, "claim", value_type=bool),
                "status": get_value(relative, "status"),
            }
            for relative in employee.relative_ids
        ]
