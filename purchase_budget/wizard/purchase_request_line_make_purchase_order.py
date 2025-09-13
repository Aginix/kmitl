import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import get_lang

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        res = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        active_id = self.env.context.get("active_id", False)
        purchase = self.env['purchase.order'].browse(active_id)
        res["date_range_fy_id"] = purchase.date_range_fy_id.id
        res["analytic_distribution"] = purchase.analytic_distribution
        res["budget_commitment_id"] = purchase.budget_commitment_id.id
        res["budget_account_id"] = purchase.budget_account_id.id
        res["procurement_plan_id"] = purchase.procurement_plan_id.id
        res["procurement_plan_analytic_id"] = purchase.procurement_plan_analytic_id.id
        return res
