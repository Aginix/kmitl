# -*- coding: utf-8 -*-
import logging

from datetime import datetime

from odoo import api, fields, models

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
    title = fields.Char(
        string="title",
        required=True
    )
    description = fields.Text(string="reason", required=True)
    current_user = fields.Many2one(
        'res.users',
        string="Current User",
        compute='_compute_current_user',
        store=True,
    )
    payment_type = fields.Selection([
        ("direct", "Direct paid"),
        ("loan", "Loan"),
        ("prepaid", "Prepaid")
    ])
    contract_type = fields.Selection([
        ('order', 'Purchase/Hire Order'),
        ('contract_buy', 'Contract buy'),
        ('contract_construction', 'Contract construction'),
    ], string="Contract type", required=True)
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        related="requested_by.employee_ids.department_id",
        store=True,
        readonly=True,
    )
    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
        tracking=True,
        readonly=False,
    )

    hide_create_po_button = fields.Boolean(compute="_hide_create_po_button")

    @api.depends_context('uid')
    def _compute_current_user(self):
        for rec in self:
            rec.current_user = self.env.user

    @api.depends('state')
    def _hide_create_po_button(self):
        for rec in self:
            rec.hide_create_po_button = True
            if rec.state in ('approved', 'in_progress') and rec.purchase_count == 0:
                rec.hide_create_po_button = False
