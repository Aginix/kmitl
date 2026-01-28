# -*- coding: utf-8 -*-
from odoo import models, api


class BudgetAppropriationReportF3P005(models.AbstractModel):
    _name = "budget.appropriation.report.f3.p.005"
    _description = "สรุปประมาณการรายรับและรายจ่าย (F3-P-วง-005)"

    @api.model
    def get_data(self, filters=None):
        """Get report data - placeholder"""
        return {"data": [], "filters": filters or {}}

    @api.model
    def get_filter_options(self):
        """Get available filter options"""
        return {
            "fiscal_years": self._get_fiscal_year_options(),
        }

    def _get_fiscal_year_options(self):
        data = self.env["account.fiscal.year"].search([], order="date_from DESC")
        return [{"id": n.id, "name": n.name} for n in data]
