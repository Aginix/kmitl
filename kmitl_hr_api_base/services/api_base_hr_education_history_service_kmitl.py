from odoo import models

from ..utils.model_helper import get_value


class ApiBaseHrEducationHistoryServiceKmitl(models.AbstractModel):
    _name = "api.base.hr.education.history.service.kmitl"
    _description = "Education History Service for API Base"

    def get_education_history_by_identifier(self, identifier):
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

        if not employee:
            return None

        return [
            {
                "id": eh.id,
                "education_level_id": get_value(eh.education_level_id, "name"),
                "faculty_id": get_value(eh.faculty_id, "name"),
                "department_id": get_value(eh.department_id, "name"),
                "program_id": get_value(eh.program_id, "name"),
                "start_year": get_value(eh, "start_year", value_type=int),
                "graduation_year": get_value(eh, "graduation_year", value_type=int),
                "country": get_value(eh, "country"),
                "university_name": get_value(eh, "university_name"),
                "university_name_th": get_value(eh, "university_name_th"),
            }
            for eh in employee.education_history_ids
        ]
