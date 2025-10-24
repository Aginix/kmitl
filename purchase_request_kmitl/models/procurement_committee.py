# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProcurementCommittee(models.Model):
    _inherit = 'procurement.committee'

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
    approve_role = fields.Selection(
        selection_add=[
            ("secretary", "Secretary"),
        ],
        required=True,
        ondelete={'chairman': 'set default', 'committee': 'set default', 'secretary': 'set default'},
        default="committee",
    )
