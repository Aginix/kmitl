# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import get_lang


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_model = self.env.context.get("active_model", False)
        if active_model != "purchase.request":
            return res

        active_id = self.env.context.get("active_id", False)
        request_id = self.env[active_model].browse(active_id)
        if not request_id:
            return res

        if request_id.partner_id:
            res["supplier_id"] = request_id.partner_id.id
        return res
