# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DisbursementRequest(models.Model):
    _inherit = 'disbursement.request'

    @api.model_create_multi
    def create(self, vals_list):
        disbursement_requests = super().create(vals_list)

        for record in disbursement_requests:
            record._attach_existing_attachments_from_purchase_order()

        return disbursement_requests

    def _attach_existing_attachments_from_purchase_order(self):
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'purchase.order'),
            ('res_id', '=', self.purchase_id.id)
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
                'description': _(f'From PO: {self.purchase_id.name}'),
            }
