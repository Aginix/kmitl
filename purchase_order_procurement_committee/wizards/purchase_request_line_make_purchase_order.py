# -*- coding: utf-8 -*-
import logging

from odoo import _, Command, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    def make_purchase_order(self):
        res = super().make_purchase_order()
        # self._create_work_acceptance_committees(res)
        return res
    
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        res = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        active_id = self.env.context.get("active_id", False)
        purchase_request = self.env['purchase.request'].browse(active_id)
        if purchase_request.is_required_approval:

            wa_vals = []
            eva_vals = []
            for wa_committee in purchase_request.work_acceptance_committee_ids:
                wa_vals.append({
                    'name': wa_committee.name,
                    'employee_id': wa_committee.employee_id.id,
                    'committee_type': wa_committee.committee_type,
                    'approve_role': wa_committee.approve_role,
                    'note': wa_committee.note,
                })
            res['work_acceptance_committee_ids'] = [Command.create(val) for val in wa_vals]

            for eva_committee in purchase_request.evaluation_committee_ids:
                eva_vals.append({
                    'name': eva_committee.name,
                    'employee_id': eva_committee.employee_id.id,
                    'committee_type': eva_committee.committee_type,
                    'approve_role': eva_committee.approve_role,
                    'note': eva_committee.note,
                })
            res['evaluation_committee_ids'] = [Command.create(val) for val in eva_vals]
        return res

            # res['work_acceptance_committee_ids'] = [
            #     Command.create(
            #         {
            #             'name': committee.name,
            #             'employee_id': committee.employee_id.id,
            #             'committee_type': committee.committee_type,
            #             'approve_role': committee.approve_role,
            #             'note': committee.note,
            #         }
            #     )
            #     for val in purchase_request.work_acceptance_committee_ids
            # ]

            # res['evaluation_committee_ids'] = [
            #     Command.create(
            #         {
            #             'name': committee.name,
            #             'employee_id': committee.employee_id.id,
            #             'committee_type': committee.committee_type,
            #             'approve_role': committee.approve_role,
            #             'note': committee.note,
            #         }
            #     )
            #     for val in purchase_request.evaluation_committee_ids
            # ]
        # return res
    

    # def _create_work_acceptance_committees(self, res):
    #     po_id = res['domain'][0][2]
    #     purchase_order = self.env['purchase.order'].browse(po_id)
    #     requests = self.item_ids.mapped('request_id')
    #     for request in requests:
    #         request_committees = self.env['procurement.committee'].search([('request_id', '=', request.id), ('committee_type', 'in', ['work_acceptance', 'evaluation'])])
    #         for committee in request_committees:
    #             self.env['procurement.committee'].create({
    #                 'name': committee.name,
    #                 'purchase_order_id': purchase_order.id,
    #                 'employee_id': committee.employee_id.id,
    #                 'committee_type': committee.committee_type,
    #                 'approve_role': committee.approve_role,
    #                 'note': committee.note,
    #             })
                
