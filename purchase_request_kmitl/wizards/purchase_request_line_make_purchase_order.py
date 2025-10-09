# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        vals = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        vals.update({
            "operating_unit_id": self.item_ids.request_id.operating_unit_id.id,
            "account_fiscal_year_id": self.item_ids.request_id.account_fiscal_year_id.id
        })
        return vals

    def make_purchase_order(self):
        for item in self.item_ids:
            line = item.line_id
            if line.purchase_lines:
                raise UserError(_(
                    "The purchase request '%s' already has a Purchase Order."
                ) % line.display_name)

        res = super().make_purchase_order()
        self._create_work_acceptance_committees(res)
        return res

    def _create_work_acceptance_committees(self, res):
        po_id = res['domain'][0][2]
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

class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order.item'

    keep_description = fields.Boolean(
        default=True,
    )
    keep_estimated_cost = fields.Boolean(
        default=True,
    )
