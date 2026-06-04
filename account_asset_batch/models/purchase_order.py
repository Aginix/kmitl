# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    asset_count = fields.Integer(
        string="Assets",
        compute="_compute_asset_count",
    )

    def _compute_asset_count(self):
        for po in self:
            po.asset_count = self.env['account.asset.batch'].search_count([
                ('purchase_id', '=', po.id)
            ])

    def action_open_asset_batch(self):    
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_asset_batch.action_asset_batch_procurement"
        )
        action["domain"] = [("purchase_id", "=", self.id)]
        action["context"] = {
            "default_purchase_id": self.id,
            "create": True,
            "default_account_fiscal_year_id": self.account_fiscal_year_id.id,
            "default_department_analytic_id": self.department_analytic_id.id,
        }
        return action