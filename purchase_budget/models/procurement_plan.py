import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    purchase_order_count = fields.Integer(
        string="Purchase Orders Count", compute="_compute_purchase_order_count"
    )

    @api.depends("purchase_order_ids")
    def _compute_purchase_order_count(self):
        for record in self:
            record.purchase_order_count = len(record.purchase_order_ids)

    purchase_order_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="procurement_plan_id",
        string="Purchase Orders",
    )

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            "name": "Purchase Order",
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.purchase_order_ids.ids)],
        }

    def _get_open_downstream_documents(self):
        """A purchase order not yet done (เสร็จสิ้น) or cancelled keeps the plan
        from being closed or deleted (procurement_plan ADR-0005)."""
        res = super()._get_open_downstream_documents()
        count = (
            self.env["purchase.order"]
            .sudo()
            .search_count(
                [
                    ("procurement_plan_id", "=", self.id),
                    ("state", "not in", ("done", "cancel")),
                ]
            )
        )
        if count:
            res.append(_("ใบสั่งซื้อ/สัญญา (PO) ที่ยังไม่เสร็จสิ้น %s รายการ") % count)
        return res
