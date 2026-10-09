from odoo import http
import json
from werkzeug.wrappers import Response
from .employee_response import EmployeeResponse


class Employee(http.Controller):
    def __ErrorResponse(self, message, status=400):
        headers = {"Content-Type": "application/json"}
        return Response(json.dumps({"message": message}), status, headers)

    def __check_limit(self, value, limit=None):
        value = int(value)
        if value < 0:
            raise ValueError(
                "Invalid parameter, page and size must 0, positive integer only"
            )
        if limit is None:
            return value
        return min(value, limit)

    @http.route("/api/advance/employee_list", auth="api_key", methods=["GET"])
    def employee_list(self, page=1, size=10, **kwargs):
        try:
            page = self.__check_limit(page)
            size = self.__check_limit(size, 1000)
        except (ValueError, TypeError):
            return self.__ErrorResponse(
                "Invalid parameter, page and size must positive integer only", 400
            )

        offset = (page - 1) * size

        employees = http.request.env["hr.employee"].search(
            [],
            limit=size,
            offset=offset,
            order="code",
        )

        count = http.request.env["hr.employee"].search_count([])
        api_key = http.request.httprequest.headers.get("Api-Key")

        employees_array = []
        for employee in employees:
            employeeResponse = EmployeeResponse(employee, api_key)
            employees_array.append(employeeResponse.to_json())

        headers = {"Content-Type": "application/json"}
        body = json.dumps(
            {"data": employees_array, "total": count},
            indent=4,
            sort_keys=True,
            default=str,
        )
        return Response(body, headers=headers)

    @http.route("/api/advance/employee_search", auth="api_key", methods=["GET"])
    def employee_search(self, **kwargs):
        if not kwargs.get("email") and not kwargs.get("kmitl_code"):
            return self.__ErrorResponse(
                "Invalid parameter, email or kmitl_code is required", 400
            )

        employee = (
            http.request.env["hr.employee"]
            .with_context(lang="th_TH", active_test=False)
            .search(
                [
                    "|",
                    ("work_email", "=", kwargs.get("email", "")),
                    ("code", "=", kwargs.get("kmitl_code", "")),
                ],
                limit=1,
            )
        )
        api_key = http.request.httprequest.headers.get("Api-Key")

        if not employee:
            return self.__ErrorResponse("Employee not found", 404)

        employeeResponse = EmployeeResponse(employee, api_key)

        headers = {"Content-Type": "application/json"}
        body = json.dumps(
            employeeResponse.to_json(), indent=4, sort_keys=True, default=str
        )
        return Response(body, headers=headers)
