# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        vals = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        vals.update({
            "operating_unit_id": self.item_ids.request_id.operating_unit_id.id,
            "account_fiscal_year_id": self.item_ids.request_id.account_fiscal_year_id.id,
            "requesting_operating_unit_id": self.item_ids.request_id.operating_unit_id.id,
            "payment_type": self.item_ids.request_id.payment_type,
        })
        return vals

    def make_purchase_order(self):
        for item in self.item_ids:
            line = item.line_id
            if line.purchase_lines:
                raise UserError(_(
                    "The purchase request '%s' already has a Purchase Order."
                ) % line.display_name)

        res = super().make_purchase_order()
        self._post_chatter_messages_after_po_creation()
        return res

    def _post_chatter_messages_after_po_creation(self):
        purchase_orders = self.item_ids.mapped("line_id.purchase_lines.order_id")
        purchase_requests = self.item_ids.mapped("line_id.request_id")
        if not purchase_orders or not purchase_requests:
            return
        for po in purchase_orders:
            pr_items = "".join(
                '<li><a href="%s" target="_blank">%s</a></li>' % (pr._get_record_url(), pr.name)
                for pr in purchase_requests
            )
            po.message_post(
                body=_("Created from Purchase Request:<ul>%s</ul>") % pr_items,
                subtype_xmlid="mail.mt_note",
            )
        for pr in purchase_requests:
            po_items = "".join(
                '<li><a href="/web#id=%d&model=purchase.order&view_type=form" target="_blank">%s</a></li>'
                % (po.id, po.name)
                for po in purchase_orders
            )
            pr.message_post(
                body=_("Purchase Order created:<ul>%s</ul>") % po_items,
                subtype_xmlid="mail.mt_note",
            )


class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order.item'

    keep_description = fields.Boolean(
        default=True,
    )
    keep_estimated_cost = fields.Boolean(
        default=True,
    )
