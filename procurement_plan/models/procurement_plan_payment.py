import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProcurementPlanPayment(models.Model):
    _name = "procurement.plan.payment"
    _description = "Procurement Plan Payment"

    MONTH_SELECTION = [
        ("01", "January"),
        ("02", "February"),
        ("03", "March"),
        ("04", "April"),
        ("05", "May"),
        ("06", "June"),
        ("07", "July"),
        ("08", "August"),
        ("09", "September"),
        ("10", "October"),
        ("11", "November"),
        ("12", "December"),
    ]

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan", readonly=True
    )
    number = fields.Integer("Installment Number", default=1)
    number_of_days = fields.Integer("Number of Days")
    month = fields.Selection(MONTH_SELECTION, "Payment Disbursement Date (Month)")
    amount = fields.Float("Payment Amount")
    state = fields.Selection(related="procurement_plan_id.state")
