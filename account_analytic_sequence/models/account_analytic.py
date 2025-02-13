import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountAnalytic(models.Model):
    _inherit = "account.analytic"
    _order = "sequence, name"

    sequence = fields.Integer(default=50)
