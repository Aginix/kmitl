from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import get_lang


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    estimated_cost = fields.Float(compute="_compute_estimated_cost")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_model = self.env.context.get("active_model", False)

        if active_model == "purchase.request":
            request_ids = self.env.context.get("active_ids", False)
            purchase_request = self.env[active_model].browse(request_ids)

            if purchase_request.partner_id:
                res['supplier_id'] = purchase_request.partner_id.id

        return res

    @api.depends("item_ids.estimated_cost")
    def _compute_estimated_cost(self):
        for rec in self:
            rec.estimated_cost = sum(rec.item_ids.mapped('estimated_cost'))
