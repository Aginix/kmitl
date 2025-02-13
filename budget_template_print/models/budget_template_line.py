import logging

from odoo import models

_logger = logging.getLogger(__name__)


class BudgetTemplateLine(models.Model):
    _inherit = "budget.template.line"
