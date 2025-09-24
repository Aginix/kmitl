# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    analytic_distribution = fields.Json(
        'Analytic',
        compute="_compute_analytic_distribution", store=True, copy=True, readonly=False,
        related='request_id.analytic_distribution'
    )
