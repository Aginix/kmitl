# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    tor_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="TOR Committees",
        domain=[("committee_type", "=", "tor_committee")],
        copy=True,
    )

    price_determine_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Price Determine Committees",
        domain=[("committee_type", "=", "price_determine")],
        copy=True,
    )

    evaluation_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Evaluation Committees",
        domain=[("committee_type", "=", "evaluation")],
        copy=True,
    )

    hide_create_po_button = fields.Boolean(compute="_hide_create_po_button")

    @api.depends('state')
    def _hide_create_po_button(self):
        for rec in self:
            rec.hide_create_po_button = True
            if rec.state in ('approved', 'in_progress') and rec.purchase_count == 0:
                rec.hide_create_po_button = False
