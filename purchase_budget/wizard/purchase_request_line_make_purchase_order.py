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
        purchase_request = self.env['purchase.request'].browse(active_id)
        res["account_fiscal_year_id"] = purchase_request.account_fiscal_year_id.id
        res["analytic_distribution"] = purchase_request.analytic_distribution
        res["budget_commitment_id"] = purchase_request.budget_commitment_id.id
        res["budget_account_id"] = purchase_request.budget_account_id.id
        res["use_procurement_plan"] = purchase_request.require_procurement_plan
        res["procurement_plan_id"] = purchase_request.procurement_plan_id.id
        res["procurement_plan_analytic_id"] = purchase_request.procurement_plan_analytic_id.id
        return res
