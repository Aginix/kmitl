# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestApproval(models.Model):
    _inherit = 'purchase.request.approval'

    @api.model_create_multi
    def create(self, vals_list):
        approvals = super().create(vals_list)
        
        for approval in approvals:
            if approval.request_id:
                approval._copy_attachments_from_request(approval)
        
        return approvals

    def _copy_attachments_from_request(self, pa_record):
        Attachment = self.env['ir.attachment']

        pr_attachments = Attachment.search([
            ('res_model', '=', 'purchase.request'),
            ('res_id', '=', self.request_id.id)
        ])

        for attachment in pr_attachments:
            Attachment.create({
                'name': attachment.name,
                'datas': attachment.datas,  
                'res_model': pa_record._name,
                'res_id': pa_record.id,
                'type': attachment.type,
                'mimetype': attachment.mimetype,
                'description': f'From PR: {self.request_id.name}',
            })