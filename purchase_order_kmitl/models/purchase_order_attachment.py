# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrderAttachment(models.Model):
    _name = 'purchase.order.attachment'
    _description = 'Purchase Order Attachment'

    request_id = fields.Many2one("purchase.order", string="Purchase Request")
    file_name = fields.Char(string="Filename")
    file = fields.Binary(string="File", required=True)
    description = fields.Char(string="Description")
