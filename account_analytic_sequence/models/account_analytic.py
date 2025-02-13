import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"
    _order = "sequence, name"

    sequence = fields.Integer(default=50)
