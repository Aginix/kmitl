# -*- coding: utf-8 -*-
from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    sequence = fields.Integer(string="Sequence")
