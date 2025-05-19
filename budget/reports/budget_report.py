import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetReport(models.AbstractModel):
    _name = "budget.report"
    _description = "Budget Report"

    @api.model
    def get_html(self, template_id, domain):
        return {}

    def _get_budget_template(self, template_id):
        pass

    def add_column(self):
        pass

    def add_datasource(self):
        pass
