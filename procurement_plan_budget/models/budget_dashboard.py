from odoo import models


class BudgetDashboard(models.AbstractModel):
    """Contribute a แผนจัดซื้อจัดจ้าง section to the budget overview.

    The overview is open for extension: budget core renders whatever
    ``_overview_sections`` returns, without knowing about the procurement_plan
    dimension. We append one section here, scoped to the same fiscal year /
    source / department filters as the cards.
    """

    _inherit = "budget.dashboard"

    def _overview_sections(self, fiscal_year_id, source_id, department_ids=None):
        sections = super()._overview_sections(
            fiscal_year_id, source_id, department_ids
        )
        items = self._dim_section_items(
            "procurement_plan_analytic_id", fiscal_year_id, source_id, department_ids
        )
        if items:
            sections.append(
                {
                    "key": "procurement_plan",
                    "title": "แผนจัดซื้อจัดจ้าง",
                    "drill_dim": "procurement_plan_analytic_id",
                    "items": items,
                }
            )
        return sections
