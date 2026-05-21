# -*- coding: utf-8 -*-
from odoo.addons.budget_appropriation_summary.controllers.main import (
    BudgetAppropriationSummaryController,
)

# Register F24 with the upstream report map so the existing
# /budget_appropriation_summary/<id>/report/<name>/<type> route handles
# F24 without re-declaring an overlapping route.
BudgetAppropriationSummaryController.MASTER_SUMMARY_REPORT_MAP = {
    **BudgetAppropriationSummaryController.MASTER_SUMMARY_REPORT_MAP,
    "f24": "budget_appropriation_summary_f24.action_report_compilation_f24",
}
