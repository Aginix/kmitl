from odoo.http import request, Response
from odoo import http
from .api_key_jwt import ApiKeyJWT
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError


class EmployeeImage(http.Controller):
    def __init__(self):
        self.__jwtSerice = ApiKeyJWT()

    @http.route("/employee/image", type="http", auth="none", cors="*")
    def content_image(self, token=None):
        if not (token):
            return Response("Your request invalid", status=400)

        data = None
        try:
            data = self.__jwtSerice.verifyJWT(token)
        except InvalidSignatureError:
            return Response("JWT Signature Error", status=401)
        except ExpiredSignatureError:
            return Response("JWT Expired", status=401)

        employee = (
            request.env[data["model"]]
            .sudo()
            .search([("id", "=", data["model_id"])], limit=1)
        )

        if not employee:
            return Response("Not found employee id: " + data["model_id"], status=404)

        record = (
            request.env["ir.binary"]
            .sudo()
            ._find_record(None, data["model"], id and int(employee["id"]), None)
        )

        stream = request.env["ir.binary"]._get_image_stream_from(
            record,
            data["field"],
            filename="image",
            filename_field="name",
            mimetype=None,
            width=int(0),
            height=int(0),
            crop=False,
        )

        send_file_kwargs = {"as_attachment": False}
        send_file_kwargs["immutable"] = True
        send_file_kwargs["max_age"] = http.STATIC_CACHE_LONG

        return stream.get_response(**send_file_kwargs)
