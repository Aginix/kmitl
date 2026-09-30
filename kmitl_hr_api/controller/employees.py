import json

from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request

from ..services.private_contact_service import HrEmployeePrivateContactService
from ..services.relative_service import HrEmployeeRelativeService
from .employee_contract_response import EmployeeContractResponse
from .employee_response import EmployeeResponse


class Employee(http.Controller):
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
        "/api/v1/employees/<string:identifier>/private_contact",
        auth="api_key",
        methods=["GET"],
    )
    def get_employee_private_contact(self, identifier):
        employee = (
            http.request.env["hr.employee"]
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
            return self.__ErrorResponse("Employee not found", 404)

        service = HrEmployeePrivateContactService(request)
        result = service.get_private_contact(identifier)

        headers = {"Content-Type": "application/json"}
        body = json.dumps(result, indent=4, sort_keys=True, default=str)
        return Response(body, headers=headers)

    @http.route(
        "/api/v1/employees/<string:identifier>/contracts",
        auth="api_key",
        methods=["GET"],
    )
    def get_employee_contract(self, identifier):
        employee = (
            http.request.env["hr.employee"]
            .with_context(lang="th_TH", active_test=False)
            .search(
                ["|", ("code", "=", identifier), ("work_email", "=", identifier)],
                limit=1,
            )
        )

        if not employee:
            return self.__ErrorResponse("Employee not found", 404)

        employeeResponse = EmployeeContractResponse(employee)
        headers = {"Content-Type": "application/json"}
        body = json.dumps(
            employeeResponse.to_json(), indent=4, sort_keys=True, default=str
        )
        return Response(body, headers=headers)

    @http.route(
        [
            "/api/v1/employees/<string:identifier>/relative",
            "/api/v1/employees/<string:identifier>/relatives",
        ],
        auth="api_key",
        methods=["GET"],
    )
    def get_employee_relative(self, identifier):
        employee = (
            http.request.env["hr.employee"]
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
            return self.__ErrorResponse("Employee not found", 404)

        service = HrEmployeeRelativeService(request)
        result = service.get_relatives(identifier)

        headers = {"Content-Type": "application/json"}
        body = json.dumps(result, indent=4, sort_keys=True, default=str)
        return Response(body, headers=headers)

    @http.route(
        "/api/v1/employees/<string:identifier>", auth="api_key", methods=["GET"]
    )
    def get_employee(self, identifier):
        employee = (
            http.request.env["hr.employee"]
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
        headers = {"Content-Type": "application/json"}
        api_key = http.request.httprequest.headers.get("Api-Key")

        if not employee:
            return self.__ErrorResponse("Employee not found", 404)

        employeeResponse = EmployeeResponse(employee, api_key)
        body = json.dumps(
            employeeResponse.to_json(), indent=4, sort_keys=True, default=str
        )

        return Response(body, headers=headers)

    @http.route("/api/v1/employees", auth="api_key", methods=["GET"])
    def get_employees(self, page=1, limit=25):
        try:
            page = self.__check_limit(page)
            limit = self.__check_limit(limit, 500)
        except Exception:
            return self.__ErrorResponse(
                "Invalid parameter, page and limit must 0, positive integer only", 400
            )

        skip_record = (page - 1) * limit

        employees = (
            http.request.env["hr.employee"]
            .with_context(lang="th_TH", active_test=False)
            .search([("code", "!=", "")], limit=limit, offset=skip_record, order="code")
        )
        count = (
            http.request.env["hr.employee"]
            .with_context(active_test=False)
            .search_count([("code", "!=", "")])
        )
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
