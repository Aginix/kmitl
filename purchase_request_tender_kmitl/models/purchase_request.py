# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    tender_ids = fields.One2many(comodel_name="purchase.request.tender", inverse_name="request_id", string="purchase request tender")
    tender_count = fields.Integer(compute="_compute_tender_count")

    def _compute_tender_count(self):
        for rec in self:
            rec.tender_count = len(rec.tender_ids)

    def action_view_purchase_request_tender(self):
        self.ensure_one()

        return {
            'name': 'Purchase Request Tender',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request.tender',
            'view_mode': 'tree',
            'domain': [('request_id', '=', self.id)],
            'context': {
                'default_request_id': self.id,
            },
            'target': 'current',
        }
