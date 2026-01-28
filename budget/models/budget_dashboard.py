from odoo import api, models


class BudgetDashboard(models.TransientModel):
    _name = "budget.dashboard"
    _description = "Budget Dashboard"

    @api.model
    def get_filter_options(self):
        """Get available options for filters."""
        fiscal_years = self.env["account.fiscal.year"].search([], order="name desc")
        return {
            "fiscal_years": [
                {"id": fy.id, "name": fy.name}
                for fy in fiscal_years
            ],
        }

    @api.model
    def get_dashboard_data(self, filters):
        """Get dashboard statistics based on filters."""
        domain = [("move_id.state", "=", "posted")]

        if filters.get("fiscal_year_id"):
            domain.append(("move_id.account_fiscal_year_id", "=", filters["fiscal_year_id"]))

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
