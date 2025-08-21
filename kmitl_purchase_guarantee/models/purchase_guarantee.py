# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseGuarantee(models.Model):
    _inherit = 'purchase.guarantee'

    reference = fields.Reference(
        selection_add=[
            ("purchase.guarantee", "Guarantee")
        ]
    )

    document_ref = fields.Text()

    # รอเชื่อมกับของพี่แชมป์
    receive_contract_ref = fields.Char()

    # รอเชื่อมกับของพี่แชมป์
    return_contract_ref = fields.Char()

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') in ('New', '/'):
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.guarantee.custom') or '/'
        return super(PurchaseGuarantee, self).create(vals)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'guarantee_method_id' in fields_list:
            if not defaults.get('guarantee_method_id') and not defaults.get('reference'):
                method = self.env['purchase.guarantee.method'].search([
                    ('default_for_model', '=', 'purchase.guarantee')
                ], limit=1)
                if method:
                    defaults['guarantee_method_id'] = method.id
        return defaults

    @api.depends("reference")
    def _compute_reference(self):
        for rec in self.filtered("reference"):
            if rec.reference._name == "purchase.requisition":
                rec.requisition_id = rec.reference
                rec.reference_model = rec.reference._name
            elif rec.reference._name == "purchase.order":
                rec.purchase_id = rec.reference
                if rec.reference.state in ["draft", "sent"]:
                    rec.reference_model = "{}.{}".format(rec.reference._name, "rfq")
                elif rec.reference.state in ["purchase"]:
                    rec.reference_model = "{}.{}".format(rec.reference._name, "po")
            else:
                rec.reference_model = "purchase.guarantee"
            rec._check_reference_status()

    @api.depends("reference")
    def _compute_guarantee_method_id(self):
        GuaranteeMethod = self.env["purchase.guarantee.method"]
        for rec in self.filtered("reference"):
            dom = []
            if rec.reference._name == "purchase.requisition":
                dom = [("default_for_model", "=", rec.reference._name)]
            elif rec.reference._name == "purchase.order":
                if rec.reference.state in ["draft", "sent"]:
                    dom = [
                        (
                            "default_for_model",
                            "=",
                            "{}.{}".format(rec.reference._name, "rfq"),
                        )
                    ]
                elif rec.reference.state in ["purchase"]:
                    dom = [
                        (
                            "default_for_model",
                            "=",
                            "{}.{}".format(rec.reference._name, "po"),
                        )
                    ]
            else:
                dom = [("default_for_model", "=", "purchase.guarantee")]
            rec.guarantee_method_id = GuaranteeMethod.search(dom)[:1]