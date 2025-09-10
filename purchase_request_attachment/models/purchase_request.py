# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        string='Document Attachments',
        tracking=True,
    )