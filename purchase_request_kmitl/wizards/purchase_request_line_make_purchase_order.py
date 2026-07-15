# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        vals = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        vals.update({
            "operating_unit_id": self.item_ids.request_id.operating_unit_id.id,
            "account_fiscal_year_id": self.item_ids.request_id.account_fiscal_year_id.id,
            "requesting_operating_unit_id": self.item_ids.request_id.operating_unit_id.id,
            "payment_type": self.item_ids.request_id.payment_type,
            "procurement_method_id": self.item_ids.request_id.procurement_method_id.id,
        })
        return vals

    def make_purchase_order(self):
        for item in self.item_ids:
            line = item.line_id
            if line.purchase_lines:
                raise UserError(
                    _("The purchase request '%s' already has a Purchase Order.", line.display_name)
                )
        return super().make_purchase_order()


class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order.item"

    keep_description = fields.Boolean(
        default=True,
    )
    keep_estimated_cost = fields.Boolean(
        default=True,
    )
