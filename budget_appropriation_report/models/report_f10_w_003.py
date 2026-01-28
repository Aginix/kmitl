# -*- coding: utf-8 -*-
from odoo import models, api


class BudgetAppropriationReportF10W003(models.AbstractModel):
    _name = "budget.appropriation.report.f10.w.003"
    _description = "สรุปประมาณการรายจ่าย จําแนกตามแผนงาน-งานและงบรายจ่าย (F10-W-วง-003)"

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
