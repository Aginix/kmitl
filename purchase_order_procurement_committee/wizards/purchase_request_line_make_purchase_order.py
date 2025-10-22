# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    def make_purchase_order(self):
        res = super().make_purchase_order()
        self._create_work_acceptance_committees(res)
        return res

    def _create_work_acceptance_committees(self, res):
        po_id = res['domain'][0][2] if res['domain'] else res['res_id']
        purchase_order = self.env['purchase.order'].browse(po_id)
        requests = self.item_ids.mapped('request_id')
        for request in requests:
            request_committees = self.env['procurement.committee'].search([('request_id', '=', request.id), ('committee_type', 'in', ['work_acceptance', 'evaluation'])])
            for committee in request_committees:
                self.env['procurement.committee'].create({
                    'name': committee.name,
                    'purchase_order_id': purchase_order.id,
                    'employee_id': committee.employee_id.id,
                    'committee_type': committee.committee_type,
                    'approve_role': committee.approve_role,
                    'note': committee.note,
                })
