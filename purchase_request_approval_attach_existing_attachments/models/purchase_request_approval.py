# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestApproval(models.Model):
    _inherit = 'purchase.request.approval'

    @api.model_create_multi
    def create(self, vals_list):
        approvals = super().create(vals_list)
        
        for record in approvals:
            record._attach_existing_attachments_from_request()
        
        return approvals
    
    def _attach_existing_attachments_from_request(self):
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'purchase.request'),
            ('res_id', '=', self.request_id.id)
        ])

        for attachment in attachments:
            self.env['ir.attachment'].create(self._prepare_existing_attachment_vals(attachment))

    def _prepare_existing_attachment_vals(self, attachment):
        return {
                'name': attachment.name,
                'datas': attachment.datas,  
                'res_model': self._name,
                'res_id': self.id,
                'type': attachment.type,
                'mimetype': attachment.mimetype,
                'description': _(f'From PR: {self.request_id.name}'),
            }
