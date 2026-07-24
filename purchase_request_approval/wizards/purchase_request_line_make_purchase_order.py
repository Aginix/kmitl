# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    vat_included = fields.Selection(
        [("exclusive", "VAT Exclusive"), ("inclusive", "VAT Inclusive")],
        default="exclusive",
    )
    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        domain="[('type_tax_use', 'in', ['purchase'])]",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        approval_id = self.env.context.get("approval_id")
        if approval_id:
            approval = self.env["purchase.request.approval"].browse(approval_id)
            if approval.exists():
                res.setdefault("vat_included", approval.vat_included)
                res.setdefault("tax_id", approval.tax_id.id)
                return res
        active_ids = self.env.context.get("active_ids") or []
        if active_ids and self.env.context.get("active_model") == "purchase.request":
            request = self.env["purchase.request"].browse(active_ids[0])
            if request.exists():
                res.setdefault("vat_included", request.vat_included)
                res.setdefault("tax_id", request.tax_id.id)
        return res

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        res = super()._prepare_purchase_order_line(po, item)
        res["taxes_id"] = [(4, item.tax_id.id)] if item.tax_id else False
        return res

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
        # item.tax_id is now related from wiz_id.tax_id — drop any snapshot
        # of PR-line tax_id set by upstream overrides.
        res.pop("tax_id", None)
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


class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order.item"

    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        related="wiz_id.tax_id",
    )
