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
    month = fields.Integer(string="Payment Disbursement Date (Month)")
    amount = fields.Float("Payment Amount")
    state = fields.Selection(related='procurement_plan_id.state')
