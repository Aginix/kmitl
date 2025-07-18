import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    vendor = fields.Many2one(
        "res.partner",
        string="Vendor",
        help="Select a vendor to create a purchase order for the selected request lines.",
    )
    start_date = fields.Date(
        string="วันที่เริ่มสัญญา",
        help="The start date for the purchase order. If not set, the current date will be used.",
    )
    end_date = fields.Date(
        string="วันที่สิ้นสุดสัญญา",
        help="The end date for the purchase order. If not set, the start date will be used.",
    )
    purchase_request_number = fields.Char(
        string="หมายเลขคำสั่งซื้อ",
        required=True,
        help="The number of the purchase request associated with the selected lines.",
    )
    purchase_type = fields.Selection(
        [("standard", "Standard"), ("urgent", "Urgent")],
        string="ประเภทสัญญา",
        required=True,
        help="Select the type of purchase order to create. Standard for regular orders, Urgent for expedited orders.",
    )
    purchase_request_name = fields.Char(
        string="ชื่อใบสั่งซื้อ/จ้าง",
        required=True,
        help="The name of the purchase request associated with the selected lines.",
    )

    request_ids = fields.Many2many(
        comodel_name="purchase.request",
        relation="purchase_request_make_po_rel",
        column1="wizard_id",
        column2="request_id",
        string="จัดกลุ่ม purchase request",
    )

    def make_purchase_order(self):
        res = []
        purchase_obj = self.env["purchase.order"]
        po_line_obj = self.env["purchase.order.line"]
        purchase = False
        purchase_requests = self.request_ids
        for item in self.item_ids:
            line = item.line_id
            if item.product_qty <= 0.0:
                raise UserError(_("Enter a positive quantity."))
            if self.purchase_order_id:
                purchase = self.purchase_order_id
                purchase.request_ids = [(4, r.id) for r in purchase_requests]
            if not purchase:
                po_data = self._prepare_purchase_order(
                    line.request_id.picking_type_id,
                    line.request_id.group_id,
                    line.company_id,
                    line.origin,
                )
                po_data["request_ids"] = [(6, 0, purchase_requests.ids)]
                purchase = purchase_obj.create(po_data)

            domain = self._get_order_line_search_domain(purchase, item)
            available_po_lines = po_line_obj.search(domain)
            new_pr_line = True

            if not line.product_uom_id:
                line.product_uom_id = item.product_uom_id

            alloc_uom = line.product_uom_id
            wizard_uom = item.product_uom_id
            if (
                available_po_lines
                and not item.keep_description
                and not item.keep_estimated_cost
            ):
                new_pr_line = False
                po_line = available_po_lines[0]
                po_line.purchase_request_lines = [(4, line.id)]
                po_line.move_dest_ids |= line.move_dest_ids
                po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                    po_line.product_uom_qty, alloc_uom
                )
                wizard_product_uom_qty = wizard_uom._compute_quantity(
                    item.product_qty, alloc_uom
                )
                all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                self.create_allocation(po_line, line, all_qty, alloc_uom)
            else:
                po_line_data = self._prepare_purchase_order_line(purchase, item)
                if item.keep_description:
                    po_line_data["name"] = item.name
                po_line = po_line_obj.create(po_line_data)
                po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                    po_line.product_uom_qty, alloc_uom
                )
                wizard_product_uom_qty = wizard_uom._compute_quantity(
                    item.product_qty, alloc_uom
                )
                all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                self.create_allocation(po_line, line, all_qty, alloc_uom)
            self._post_process_po_line(item, po_line, new_pr_line)
            res.append(purchase.id)

        purchase_requests = self.item_ids.mapped("request_id")
        purchase_requests.button_in_progress()
        return {
            "domain": [("id", "in", res)],
            "name": _("RFQ"),
            "view_mode": "tree,form",
            "res_model": "purchase.order",
            "view_id": False,
            "context": False,
            "type": "ir.actions.act_window",
        }
