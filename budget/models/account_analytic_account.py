import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"
    _order = "code"
