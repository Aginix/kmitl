# -*- coding: utf-8 -*-
from odoo import api, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        vals = super()._prepare_purchase_order(
            picking_type, group_id, company, origin
        )
        approval_id = self.env.context.get("approval_id")
        if not approval_id:
            return vals
        approval = self.env["purchase.request.approval"].browse(approval_id)
        if not approval.exists():
            return vals
        vals.update(
            {
                "account_fiscal_year_id": approval.account_fiscal_year_id.id,
                "payment_type": approval.payment_type,
                "procurement_method_id": approval.procurement_method_id.id,
            }
        )
        return vals

    @api.model
    def _prepare_item(self, line):
        res = super()._prepare_item(line)
        approval_id = self.env.context.get("approval_id")
        if not approval_id:
            return res
        approval = self.env["purchase.request.approval"].browse(approval_id)
        if not approval.exists():
            return res
        pr_lines = line.request_id.line_ids.sorted("id")
        pa_lines = approval.line_ids.sorted("id")
        try:
            idx = list(pr_lines.ids).index(line.id)
        except ValueError:
            return res
        if idx < len(pa_lines):
            pa_line = pa_lines[idx]
            res["product_qty"] = pa_line.product_qty
            res["price_unit"] = pa_line.price_unit
        return res
