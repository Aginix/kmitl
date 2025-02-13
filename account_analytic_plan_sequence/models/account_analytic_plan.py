import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"
    _order = "sequence, name"

    sequence = fields.Integer(default=50)
