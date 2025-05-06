# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementPlanPayment(models.Model):
    _name = "procurement.plan.payment"
    _description = "Procurement Plan Payment"

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan", readonly=True
    )
    number = fields.Integer("Installment Number", default=1)
    number_of_days = fields.Integer("Number of Days")
    month = fields.Selection(
        [
            ("10", "10/67"),
            ("11", "11/67"),
            ("12", "12/67"),
            ("1", "1/68"),
            ("2", "2/68"),
            ("3", "3/68"),
            ("4", "4/68"),
            ("5", "5/68"),
            ("6", "6/68"),
            ("7", "7/68"),
            ("8", "8/68"),
            ("9", "9/68"),
        ],
        string="Payment Disbursement Date (Month)",
    )
    amount = fields.Float("Payment Amount")
