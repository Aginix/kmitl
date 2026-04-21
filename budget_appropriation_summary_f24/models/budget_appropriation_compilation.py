# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class BudgetAppropriationCompilation(models.Model):
    _inherit = "budget.appropriation.compilation"

    def get_f24_report_data(self):
        """Prepare F24 report data for QWeb rendering."""
        self.ensure_one()
        return {}

    def action_open_f24_report(self):
        """Open F24 report in a new browser tab as HTML."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_summary/compilation/{self.id}/f24/html",
            "target": "new",
        }

    def action_print_f24_report(self):
        """Print F24 report as PDF."""
        self.ensure_one()
        return self.env.ref(
            "budget_appropriation_summary_f24.action_report_compilation_f24"
        ).report_action(self)
