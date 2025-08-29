# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseAgreementAttachment(models.Model):
    _name = 'purchase.agreement.attachment'
    _description = 'Purchase Agreement Attachment'

    agreement_id = fields.Many2one("agreement", string="Agreement")
    file_name = fields.Char(string="Filename")
    file = fields.Binary(string="File", required=True)
    description = fields.Char(string="Description")
