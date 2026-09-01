# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import http
from odoo.http import request


class NoRoleLandingController(http.Controller):

    @http.route("/iam/no-role", type="http", auth="user", website=False)
    def no_role_page(self, **kwargs):
        user = request.env.user.sudo()
        if not user._is_role_gated():
            return request.redirect("/web")
        ICP = request.env["ir.config_parameter"].sudo()
        contact_message = ICP.get_param(
            "iam_no_role_landing.contact_message",
            default="กรุณาติดต่อผู้ดูแลระบบ (IAM Manager) "
            "เพื่อขอกำหนดสิทธิ์การใช้งาน",
        )
        return request.render(
            "iam_no_role_landing.no_role_page",
            {
                "user_name": user.name,
                "contact_message": contact_message,
            },
        )

    @http.route("/iam/check-role", type="json", auth="user")
    def check_role(self, **kwargs):
        user = request.env.user.sudo()
        return {"has_role": not user._is_role_gated()}
