# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProcurementCommittee(models.Model):
    _inherit = 'procurement.committee'

    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        ondelete="cascade",
        index=True,
    )
    mobile_phone = fields.Char(
        string="Mobile Phone",
        related="employee_id.mobile_phone",
        store=False,
        readonly=True,
    )
    committee_type = fields.Selection(
        selection_add=[
            ("tor_committee", "TOR Committee"),
            ("price_determine", "Price Determine Committee"),
            ("evaluation", "Evaluation Committee"),
        ],
    )
