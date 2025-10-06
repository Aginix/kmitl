# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    work_acceptance_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="purchase_order_id",
        string="Work Acceptance Committees",
        domain=[("committee_type", "=", "work_acceptance")],
        copy=True,
    )
    tor_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="purchase_order_id",
        string="TOR Committees",
        domain=[("committee_type", "=", "tor_committee")],
        copy=True,
    )
    price_determine_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="purchase_order_id",
        string="Price Determine Committees",
        domain=[("committee_type", "=", "price_determine")],
        copy=True,
    )
    evaluation_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="purchase_order_id",
        string="Evaluation Committees",
        domain=[("committee_type", "=", "evaluation")],
        copy=True,
    )
