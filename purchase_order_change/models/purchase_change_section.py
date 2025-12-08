# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseChangeSection(models.Model):
    _name = 'purchase.change.section'
    _description = 'Purchase Change Section'

    name = fields.Char('Name')

    section_type = fields.Selection(
        selection=[('addition', 'Addition'),
                   ('deletion', 'Deletion'),
                   ('modification', 'Modification')
                ], string='Type')

    active = fields.Boolean(string='Active', default=True)
