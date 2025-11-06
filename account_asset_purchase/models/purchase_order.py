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

    has_storable_product = fields.Boolean(
        string="Has Storable Product",
        compute="_compute_has_storable_product",
        store=False,
    )

    def _compute_asset_count(self):
        for po in self:
            po.asset_count = self.env['account.asset.batch'].search_count([
                ('purchase_id', '=', po.id)
            ])

    @api.depends('order_line.product_id.type')
    def _compute_has_storable_product(self):
        for po in self:
            po.has_storable_product = any(
                line.product_id.type == 'product' 
                for line in po.order_line
            )

    def action_open_asset_batch(self):    
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_asset_purchase.action_account_asset_batch"
        )
        action["domain"] = [("purchase_id", "=", self.id)]
        action["context"] = {
            "default_purchase_id": self.id,
        }
        return action