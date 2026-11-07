from odoo import http
import json
from werkzeug.wrappers import Response
from .employee_response import EmployeeResponse


class Employee(http.Controller):
    def __ErrorResponse(self, message, status=400):
        headers = {"Content-Type": "application/json"}
        return Response(json.dumps({"message": message}), status, headers)

    @http.route("/api/uapp/v1/employee", auth="api_key", methods=["GET"])
    def employee_search(self, **kwargs):
        if "email" not in kwargs:
            return self.__ErrorResponse("Invalid parameter, email is required", 400)

        email = kwargs["email"]
        employee = (
            http.request.env["hr.employee"]
            .with_context(lang="th_TH", active_test=False)
            .search([("work_email", "=", email)], limit=1)
        )

        if not employee:
            return self.__ErrorResponse("Employee not found", 404)

        employeeResponse = EmployeeResponse(employee)

        headers = {"Content-Type": "application/json"}
        body = json.dumps(
            employeeResponse.to_json(), indent=4, sort_keys=True, default=str
        )
        return Response(body, headers=headers)
