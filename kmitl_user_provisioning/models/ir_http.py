# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        """Send un-provisioned users to the "contact admin" landing page.

        Overrides the standard ``home_action_id`` (``addons/web/models/ir_http.py``)
        live, so it also applies to existing users and self-heals once the user
        is provisioned — no stored state, no group changes.
        """
        result = super().session_info()
        if request.session.uid and self.env.user._is_provisioning_locked():
            action = self.env.ref(
                "kmitl_user_provisioning.action_provisioning_notice",
                raise_if_not_found=False,
            )
            if action:
                result["home_action_id"] = action.id
        return result
