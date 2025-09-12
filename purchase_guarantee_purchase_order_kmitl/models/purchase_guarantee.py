# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseGuarantee(models.Model):
    _inherit = 'purchase.guarantee'

    is_purchase_order = fields.Boolean(
        string="Is Purchase Order",
        compute="_compute_reference",
        store=False,
        help="True if reference is purchase.order"
    )

    @api.depends("reference")
    def _compute_reference(self):
        res = super()._compute_reference()
        for rec in self:
            rec.purchase_id = False
            rec.is_purchase_order = False

            if rec.reference:
                if rec.reference._name == "purchase.order":
                    rec.purchase_id = rec.reference
                    rec.reference_model = "{}.{}".format(rec.reference._name, "po")
                    rec.is_purchase_order = True
                rec._check_reference_status()
        return res
    
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