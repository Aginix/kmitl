import json

from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request

from ..services.study_leave_service import HrStudyLeaveService


class StudyLeave(http.Controller):
    def __ErrorResponse(self, message, status=400):
        headers = {"Content-Type": "application/json"}
        return Response(json.dumps({"message": message}), status, headers)

    def __check_limit(self, value, limit=None):
        value = int(value)
        if value < 0:
            raise ValueError(
                "Invalid parameter, page and limit must 0, positive integer only"
            )
        if limit is None:
            return value
        return min(value, limit)

    @http.route(
        "/api/v1/study_leaves",
        auth="api_key",
        methods=["GET"],
    )
    # `filter` matches the HTTP query parameter name, so it cannot be renamed.
    def get_employee_study_leave(  # pylint: disable=redefined-builtin
        self, page=1, limit=25, filter=None
    ):
        service = HrStudyLeaveService(request)
        try:
            page = self.__check_limit(page)
            limit = self.__check_limit(limit, 500)
            if filter and filter not in service.filter_dict.keys():
                raise ValueError(
                    "filter must in %s only." % list(service.filter_dict.keys())
                )
        except Exception as e:
            return self.__ErrorResponse(e.args[0], 400)
        offset = (page - 1) * limit
        result = service.get_study_leaves(limit=limit, offset=offset, filter=filter)
        total = service.get_study_leaves_count(filter=filter)

        headers = {"Content-Type": "application/json"}
        body = json.dumps(
            {"data": result, "total": total},
            indent=4,
            sort_keys=True,
            default=str,
        )
        return Response(body, headers=headers)
