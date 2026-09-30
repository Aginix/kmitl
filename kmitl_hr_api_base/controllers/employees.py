import json

from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request


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
        "/api/base/v1/employees/<string:identifier>/education_histories",
        auth="api_key",
        methods=["GET"],
    )
    def get_employee_education_histories(self, identifier):
        service = request.env["api.base.hr.education.history.service.kmitl"]
        result = service.get_education_history_by_identifier(identifier)

        if not result:
            return self.__ErrorResponse("Employee not found", 404)

        headers = {"Content-Type": "application/json"}
        body = json.dumps(result, indent=4, sort_keys=True, default=str)
        return Response(body, headers=headers)

    @http.route(
        "/api/base/v1/employees/<string:identifier>", auth="api_key", methods=["GET"]
    )
    def get_employee(self, identifier):
        service = request.env["api.base.hr.employee.service.kmitl"]
        result = service.get_employee_by_identifier(identifier)

        if not result:
            return self.__ErrorResponse("Employee not found", 404)

        headers = {"Content-Type": "application/json"}
        body = json.dumps(result, indent=4, sort_keys=True, default=str)
        return Response(body, headers=headers)

    @http.route("/api/base/v1/employees", auth="api_key", methods=["GET"])
    def get_employees(self, page=1, limit=25):
        try:
            page = self.__check_limit(page)
            limit = self.__check_limit(limit, 500)
        except Exception:
            return self.__ErrorResponse(
                "Invalid parameter, page and limit must 0, positive integer only", 400
            )
        offset = (page - 1) * limit
        service = request.env["api.base.hr.employee.service.kmitl"]
        result = service.get_employees(limit=limit, offset=offset)
        total = service.get_employees_count()

        headers = {"Content-Type": "application/json"}
        body = json.dumps(
            {"data": result, "total": total},
            indent=4,
            sort_keys=True,
            default=str,
        )
        return Response(body, headers=headers)
