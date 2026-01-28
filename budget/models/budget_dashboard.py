from odoo import api, models


class BudgetDashboard(models.TransientModel):
    _name = "budget.dashboard"
    _description = "Budget Dashboard"

    @api.model
    def get_filter_options(self):
        """Get available options for filters."""
        fiscal_years = self.env["account.fiscal.year"].search([], order="name desc")
        sources = self.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "sources")],
            order="code, name",
        )
        return {
            "fiscal_years": [
                {"id": fy.id, "name": fy.name}
                for fy in fiscal_years
            ],
            "sources": [
                {"id": src.id, "name": src.name, "code": src.code}
                for src in sources
            ],
        }

    @api.model
    def get_dashboard_data(self, filters):
        """Get dashboard statistics based on filters."""
        domain = [
            ("move_id.state", "=", "posted"),
            ("move_id.account_fiscal_year_id", "=", filters["fiscal_year_id"]),
        ]

        if filters.get("source_id"):
            domain.append(("source_analytic_id", "=", filters["source_id"]))

        BudgetMoveLine = self.env["budget.move.line"]

        # งบประมาณจัดสรรทั้งหมด (appropriation moves only)
        appropriation_domain = domain + [("move_id.move_type", "=", "appropriation")]
        total_appropriation = sum(
            BudgetMoveLine.search(appropriation_domain).mapped("balance")
        )

        # งบประมาณคงเหลือ (all posted moves)
        total_balance = sum(
            BudgetMoveLine.search(domain).mapped("balance")
        )

        return {
            "total_appropriation": total_appropriation,
            "total_balance": total_balance,
        }
