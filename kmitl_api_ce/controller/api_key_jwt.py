from odoo.http import request
import jwt
from datetime import datetime, timedelta


class ApiKeyJWT:
    def getJWT(self, model, record_id, field, api_key, expire=3600):
        apikey_data = (
            request.env["auth.api.key"].sudo().search([("key", "=", api_key)], limit=1)
        )

        data = {
            "id": apikey_data["id"],
            "user_id": apikey_data["user_id"]["id"],
            "model_id": record_id,
            "model": model,
            "field": field,
            "exp": datetime.utcnow() + timedelta(seconds=expire),
        }

        return jwt.encode(data, api_key, algorithm="HS512")

    def verifyJWT(self, token):
        data = self.decodeJWTWithoutVerify(token)
        api_key = (
            request.env["auth.api.key"]
            .sudo()
            .search(
                [("user_id", "=", data["user_id"]), ("id", "=", data["id"])], limit=1
            )
        )

        return jwt.decode(token, api_key["key"], algorithms=["HS512"])

    def decodeJWTWithoutVerify(self, token):
        return jwt.decode(token, options={"verify_signature": False})
