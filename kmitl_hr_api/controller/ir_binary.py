from odoo.http import request, Response, Controller, route, STATIC_CACHE_LONG
import json
from .api_key_jwt import ApiKeyJWT
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError


class IrBinary(Controller):
    # Streaming ir_binary file.
    @route("/ir_binary/download", type="http", auth="none", cors="*")
    def get_ir_binary_stream(self, token=None):
        if not (token):
            return Response("Your request invalid", status=400)

        data = None

        try:
            data = ApiKeyJWT().verifyJWT(token)
        except InvalidSignatureError:
            return Response("JWT Signature Error", status=401)
        except ExpiredSignatureError:
            return Response("JWT Expired", status=401)

        record = (
            request.env["ir.binary"]
            .sudo()
            ._find_record(None, data["model"], id and int(data["model_id"]), None)
        )

        stream = request.env["ir.binary"]._get_stream_from(
            record=record,
            field_name=data["field"],
            filename=None,
            filename_field="name",
            mimetype=None,
            default_mimetype="application/octet-stream",
        )

        send_file_kwargs = {"as_attachment": False}
        send_file_kwargs["immutable"] = True
        send_file_kwargs["max_age"] = STATIC_CACHE_LONG

        return stream.get_response(**send_file_kwargs)

    # Generating URL with JWT
    @route("/api/v1/ir_binary", auth="api_key", methods=["POST"], csrf=False, cors="*")
    def request_ir_binary_url(self):
        json_data = json.loads(request.httprequest.data)
        api_key = request.httprequest.headers.get("Api-Key")

        # Validate mandatory fields.
        try:
            model = json_data["model"]
            record_id = json_data["id"]
            field = json_data["field"]
        except KeyError:
            return Response(
                "Mandatory fields are needed. ['model', 'ids', 'field']", status=400
            )

        # Check if model is exist.
        if not request.env["ir.model"].sudo().search([("model", "=", model)]):
            return Response("Not found model names '{}'.".format(model), status=404)

        # Validate field's properties.
        field_prop = (
            request.env["ir.model.fields"]
            .sudo()
            .search([("model", "=", model), ("name", "=", field)])
        )
        # If field is not found, return 404.
        if not field_prop:
            return Response(
                "Not found field '{}' in '{}' model.".format(field, model), status=404
            )

        if field_prop.ttype == "binary":
            field_type = "binary"
        elif field_prop.ttype == "many2many" and field_prop.relation == "ir.attachment":
            field_type = "ir.attachment"
        else:
            return Response(
                "Field '{}' in '{}' model is neither 'binary' nor 'ir.attachment'.".format(
                    field, model
                ),
                status=400,
            )

        record = request.env[model].sudo().browse(record_id)

        # Check if record is exist.
        if not record:
            return Response(
                "Not found record id:{} in '{}' model.".format(record_id, model),
                status=404,
            )

        res_body = []

        if field_type == "binary" and record[field]:
            url = ApiKeyJWT().ir_binary_url_with_jwt(api_key, model, record_id, field)

            data = {"attachment_id": None, "filename": "binary", "url": url}

            res_body.append(data)

        elif field_type == "ir.attachment":
            attachment_ids = record[field]

            for attachment in attachment_ids:
                url = ApiKeyJWT().ir_binary_url_with_jwt(
                    api_key, "ir.attachment", attachment.id, "raw"
                )

                data = {
                    "attachment_id": attachment.id,
                    "filename": attachment.name,
                    "url": url,
                }

                res_body.append(data)

        return json.dumps(res_body)
