# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseGuarantee(models.Model):
    _inherit = 'purchase.guarantee'

    is_purchase_order = fields.Boolean(
        string="Is Purchase Order",
        compute="_compute_is_purchase_order",
        store=False,
        help="True if reference is purchase.order"
    )

    @api.depends("reference")
    def _compute_is_purchase_order(self):
        for rec in self:
            if not rec.reference:
                rec.is_purchase_order = False
            elif rec.reference._name == "purchase.order":
                rec.is_purchase_order = True
            else:
                rec.is_purchase_order = False
    
    @api.depends("reference")
    def _compute_guarantee_method_id(self):
        GuaranteeMethod = self.env["purchase.guarantee.method"]
        super()._compute_guarantee_method_id()
        for rec in self.filtered("reference"):
            dom = []
            if rec.reference._name == "purchase.order":
                dom = [
                    (
                            "default_for_model",
                            "=",
                            "{}.{}".format(rec.reference._name, "po"),
                    )
                ]
            rec.guarantee_method_id = GuaranteeMethod.search(dom)[:1]

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            return
            
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': self.env.context,
        }