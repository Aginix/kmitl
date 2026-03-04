# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    partner_id = fields.Many2one("res.partner", tracking=True)

    is_required_partner_id = fields.Boolean(compute="_compute_is_required_partner_id")

    @api.depends("state", "estimated_cost")
    def _compute_is_required_partner_id(self):
        for rec in self:
            if rec.estimated_cost < 100000:
                rec.is_required_partner_id = True
            else:
                rec.is_required_partner_id = False

    @api.onchange("is_required_partner_id")
    def _onchange_is_required_partner_id(self):
        for rec in self:
            if not rec.is_required_partner_id:
                rec.partner_id = False
