# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseInvoicePlan(models.Model):
    _inherit = 'purchase.invoice.plan'

    wa_id = fields.Many2one(
        comodel_name="work.acceptance",
        compute="_compute_wa_id",
        string="Work Acceptance",
        store=False,
    )

    wa_state = fields.Selection(
        related="wa_id.state",
        string="WA State",
        store=False,
    )

    def _compute_wa_id(self):
        for rec in self:
            wa = self.env['work.acceptance'].search([('installment_id', '=', rec.id)], limit=1)
            rec.wa_id = wa