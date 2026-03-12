# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InvisibleManagementFields(models.Model):
    _name = 'invisible.management.fields'
    _description = 'Invisible Management Fields'

    management_id = fields.Many2one(
        'invisible.management',
        string='Invisible Config',
        required=True,
        ondelete='cascade',
    )

    model_id = fields.Many2one(
        'ir.model',
        related='management_id.model_id',
        store=True,
        readonly=False,
    )

    model_name = fields.Char(
        related='model_id.model',
        store=False,
        readonly=True,
    )

    field_id = fields.Many2one(
        'ir.model.fields',
        string='Field',
        required=True,
        domain="[('model_id', '=', model_id)]",
        ondelete='cascade',
    )

    domain = fields.Char(
        string='Domain',
        help="Domain to specify when the field should be invisible.",
    )

    force_invisible = fields.Boolean(
        string='Force Invisible',
        default=True,
    )

    used_field_ids = fields.Many2many(
        'ir.model.fields',
        compute='_compute_used_field_ids',
        store=False,
    )

    used_model = fields.Many2one(
        'ir.model',
        compute='_compute_used_field_ids',
        store=False,
    )

    @api.depends('management_id')
    def _compute_used_field_ids(self):
        for rec in self:
            if rec.management_id:
                rec.used_field_ids = rec.management_id.field_ids.mapped('field_id')
                rec.used_model = rec.management_id.model_id
            else:
                rec.used_field_ids = False
                rec.used_model = False
