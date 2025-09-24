# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.ondelete(at_uninstall=False)
    def _unlink_restrict_qty_accepted(self):
        for line in self:
            if line.qty_accepted > 0:
                raise UserError(
                    _("ไม่สามารถลบรายการเนื่องจากมีการรับสินค้าแล้ว")
                )
            if line.wa_line_ids:
                raise UserError(
                    _("ไม่าสามารถลบรายการเนื่องจากมีการตรวจรับสินค้าแล้ว")
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_purchase_or_done(self):
        return

    @api.constrains('product_qty')
    def _check_product_qty_vs_qty_accepted(self):
        for line in self:
            if line.product_qty < line.qty_accepted:
                raise ValidationError(
                    "Product Quantity ไม่สามารถน้อยกว่า Qty Accepted ได้"
                )
