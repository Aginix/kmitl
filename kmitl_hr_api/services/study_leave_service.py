from datetime import date

from dateutil.relativedelta import relativedelta

from ..utils.model_helper import get_value


class HrStudyLeaveService:
    filter_dict = {
        "expire_in_1_month": [
            (
                "date_end",
                "<=",
                ((date.today() + relativedelta(months=1)).strftime("%Y-%m-%d")),
            ),
            ("last_date_end_extend", "=", False),
            ("return_date", "=", False),
            ("graduated_date", "=", False),
            ("termination_date", "=", False),
        ],
        "extend_expire_in_3_month": [
            (
                "last_date_end_extend",
                "<=",
                ((date.today() + relativedelta(months=3)).strftime("%Y-%m-%d")),
            ),
            ("return_date", "=", False),
            ("graduated_date", "=", False),
            ("termination_date", "=", False),
        ],
    }

    def __init__(self, request):
        self.env = request.env

    def get_study_leaves_count(self, filter):  # pylint: disable=redefined-builtin
        search_filter = self.filter_dict[filter] if filter else []
        study_leaves_count = self.env["hr.study.leave"].search_count(search_filter)

        return study_leaves_count

    def get_study_leaves(  # pylint: disable=redefined-builtin
        self, limit=10, offset=0, filter=None
    ):
        search_filter = self.filter_dict[filter] if filter else []
        study_leaves = self.env["hr.study.leave"].search(
            search_filter,
            limit=limit,
            offset=offset,
            order="date_start, employee_id",
        )
        return [
            {
                "employee_name": get_value(study_leave.employee_id, "name"),
                "employee_kid": get_value(study_leave.employee_id, "kid"),
                "level": get_value(study_leave, "level"),
                "degree": get_value(study_leave, "degree"),
                "program": get_value(study_leave, "program"),
                "field_of_study": get_value(study_leave, "field_of_study"),
                "location": get_value(study_leave, "location"),
                "date_start": get_value(study_leave, "date_start"),
                "date_end": get_value(study_leave, "date_end"),
                "enrollment_type": get_value(study_leave, "enrollment_type"),
                "return_date": get_value(study_leave, "return_date"),
                "graduated_date": get_value(study_leave, "graduated_date"),
                "termination_date": get_value(study_leave, "termination_date"),
                "last_date_end_extend": get_value(study_leave, "last_date_end_extend"),
                "study_leave_scholarship_ids": [
                    {
                        "office_order_id": get_value(
                            scholarship.office_order_id, "ref_no"
                        ),
                        "office_order_date": get_value(
                            scholarship, "office_order_date"
                        ),
                        "type": get_value(scholarship, "type"),
                        "name": get_value(scholarship, "name"),
                    }
                    for scholarship in study_leave.study_leave_scholarship_ids
                ],
                "study_leave_extend_ids": [
                    {
                        "round_no": get_value(extend, "round_no"),
                        "date_start": get_value(extend, "date_start"),
                        "date_end": get_value(extend, "date_end"),
                        "office_order_id": get_value(extend.office_order_id, "ref_no"),
                    }
                    for extend in study_leave.study_leave_extend_ids
                ],
            }
            for study_leave in study_leaves
        ]
