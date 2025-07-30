import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    request_ids = fields.Many2many(
        comodel_name="purchase.request",
        relation="purchase_request_po_rel",
        column1="purchase_order_id",
        column2="request_id",
        string="Purchase Requests",
    )

    total_estimated_cost = fields.Monetary(
        string="Total Estimated Cost from Requests",
        compute="_compute_total_estimated_cost",
        store=True,
        currency_field="currency_id",
    )

    state = fields.Selection(
        selection_add=[
            ('egp', 'EGP'),
        ],
    )

    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        help="The department associated with this purchase order.",
    )
    request_by = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
    )
    approval_date = fields.Date(
        string="อนุมัติวันที่",
        help="The date when the purchase order was approved. If not set, it will be the current date.",
    )
    approval_by = fields.Many2one(
        "res.users",
        string="อนุมัติโดย",
        help="The user who approved the purchase order. If not set, it will be the current user.",
    )
    payment_type = fields.Selection(
        [("prepaid", "Prepaid"), ("postpaid", "Postpaid")],
        string="ประเภทการชำระเงิน",
        help="Select the payment type for this purchase order. Prepaid means payment is made before delivery, Postpaid means payment is made after delivery.",
    )
    show_egp_button = fields.Boolean(compute="_compute_show_egp_button", store=True)

    contract_start_date = fields.Date(
        string="วันที่เริ่มสัญญา",
        help="The start date for the purchase order. If not set, the current date will be used.",
    )
    contract_end_date = fields.Date(
        string="วันที่สิ้นสุดสัญญา",
        help="The end date for the purchase order. If not set, the start date will be used.",
    )

    contract_type = fields.Selection([
        ('order', 'ใบสั่งซื้อ/จ้าง'),
        ('procurement', 'สัญญาซื้อข้าย'),
        ('construction', 'สัญญาจ้างก่อสร้าง'),
    ], require=True)

    work_start_date = fields.Date(
        string="วันที่เริ่มงาน",
        help="The start date for the purchase order. If not set, the current date will be used.",
    )
    work_end_date = fields.Date(
        string="วันที่สิ้นสุดงาน",
        help="The end date for the purchase order. If not set, the start date will be used.",
    )

    purchase_request_name = fields.Char(
        string="ชื่อใบสั่งซื้อ/จ้าง",
        required=True,
        help="The name of the purchase request associated with the selected lines.",
    )

    fee = fields.Char(
        string="ค่าปรับต่อวัน"
    )

    ref_pr1 = fields.Char(
        string="Ref PR1 (พ.1)"
    )

    ref_pr2 = fields.Char(
        string="Ref PR2 (พจ.1)"
    )

    bid_line_ids = fields.One2many('purchase.order.bidder.line', 'order_id', string='รายการผู้เสนอราคา')

    document_ids = fields.One2many(
        "purchase.order.attachment",
        "request_id",
        string="แนบเอกสาร",
    )

    @api.depends("total_estimated_cost")
    def _compute_show_egp_button(self):
        for order in self:
            order.show_egp_button = order.total_estimated_cost > 100000

    @api.depends("request_ids.line_ids.estimated_cost")
    def _compute_total_estimated_cost(self):
        for order in self:
            total = 0.0
            for req in order.request_ids:
                total += sum(req.line_ids.mapped("estimated_cost"))
            order.total_estimated_cost = total

    def egp(self):
        for order in self:
            order.state = "egp"

    def egp_comfirm(self):
        for order in self:
            order.state = "purchase"