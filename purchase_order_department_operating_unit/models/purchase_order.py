# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    operating_unit_id = fields.Many2one(
        'operating.unit',
        string='Operating Unit',
        compute='_compute_operating_unit_id',
        store=True,
        readonly=False,
    )

    @api.depends('department_id.operating_unit_id')
    def _compute_operating_unit_id(self):
        for order in self:
            order.operating_unit_id = order.department_id.operating_unit_id
