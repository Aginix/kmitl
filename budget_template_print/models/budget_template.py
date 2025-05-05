import logging

from odoo import models

_logger = logging.getLogger(__name__)


class BudgetTemplate(models.Model):
    _inherit = "budget.template"
