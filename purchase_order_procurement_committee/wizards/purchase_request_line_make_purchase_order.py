# -*- coding: utf-8 -*-
import logging

from odoo import _, Command, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'
    
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        res = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        active_id = self.env.context.get("active_id", False)
        purchase_request = self.env['purchase.request'].browse(active_id)
        res['work_acceptance_committee_ids'] = [
            Command.create(self._prepare_committee(committee))
            for committee in purchase_request.work_acceptance_committee_ids
        ]
        res['work_supervisor_ids'] = [
            Command.create(self._prepare_committee(committee))
            for committee in purchase_request.work_supervisor_ids
        ]

        return res
    
    def _prepare_committee(self, committee):
        return {
            'name': committee.name,
            'employee_id': committee.employee_id.id,
            'committee_type': committee.committee_type,
            'approve_role': committee.approve_role,
            'note': committee.note,
        }
