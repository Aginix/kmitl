import base64

from odoo import http
from odoo.http import Response, request

from ..utils import jwt_helper


class EmployeeImageController(http.Controller):
    @http.route(
        "/api/base/v1/employees/<int:employee_id>/image",
        auth="public",
        methods=["GET"],
    )
    def get_employee_image(self, employee_id, **kwargs):
        token = kwargs.get("token")
        if not token:
            return Response("Missing token", status=401)

        payload = jwt_helper.decode_jwt(token)

        if payload == "expired":
            return Response("Token expired", status=401)
        elif payload is None:
            return Response("Invalid token", status=401)

        if payload.get("user_id") != employee_id:
            return Response("Unauthorized access", status=403)

        employee = request.env["hr.employee"].sudo().browse(employee_id)
        if not employee.exists():
            return Response("Employee not found", status=404)

        if not employee.image_1920:
            return Response("Image not found", status=204)

        image_data = base64.b64decode(employee.image_1920)

        return Response(image_data, content_type="image/png", status=200)
