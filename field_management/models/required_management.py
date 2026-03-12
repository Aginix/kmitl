# -*- coding: utf-8 -*-
from odoo import fields, models


class RequiredManagement(models.Model):
    _name = 'required.management'
    _description = 'Required Management'

    name = fields.Char('Name')

    active = fields.Boolean(default=True)

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
    )

    field_ids = fields.One2many(
        'required.management.fields',
        'management_id',
        string='Fields',
    )

    model_name = fields.Char(
        related='model_id.model',
        store=False,
        readonly=True,
    )

    apply_on_domain = fields.Char()

    note = fields.Text('Note')
