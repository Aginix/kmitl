import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

MONTH_SELECTION = [
    ("1", "January"),
    ("2", "February"),
    ("3", "March"),
    ("4", "April"),
    ("5", "May"),
    ("6", "June"),
    ("7", "July"),
    ("8", "August"),
    ("9", "September"),
    ("10", "October"),
    ("11", "November"),
    ("12", "December"),
]


class ProcurementPlanPayment(models.Model):
    _name = "procurement.plan.payment"
    _description = "Procurement Plan Payment"

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan", readonly=True
    )
    number = fields.Integer("Installment Number", default=1)
    number_of_days = fields.Integer("Number of Days")
    month = fields.Selection(MONTH_SELECTION, "Payment Disbursement Date (Month)")
    amount = fields.Float("Payment Amount")
    state = fields.Selection(related="procurement_plan_id.state")
