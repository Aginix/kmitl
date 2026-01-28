from odoo import api, models


class BudgetDashboard(models.TransientModel):
    _name = "budget.dashboard"
    _description = "Budget Dashboard"

    # Budget account XML IDs for each budget category
    BUDGET_CATEGORIES = [
        ("budget_account_51000", "งบบุคลากร"),
        ("budget_account_52000", "งบดำเนินงาน"),
        ("budget_account_53000", "งบลงทุน"),
        ("budget_account_54000", "งบเงินอุดหนุน"),
        ("budget_account_55000", "งบรายจ่ายอื่น"),
    ]

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

        # ร้อยละการเบิกจ่าย
        disbursement = total_appropriation - total_balance
        disbursement_percent = (
            (disbursement / total_appropriation * 100)
            if total_appropriation > 0 else 0
        )

        # Get budget breakdown by category
        budget_breakdown = self._get_budget_breakdown(domain)

        return {
            "total_appropriation": total_appropriation,
            "total_balance": total_balance,
            "disbursement": disbursement,
            "disbursement_percent": disbursement_percent,
            "budget_breakdown": budget_breakdown,
        }

    def _get_budget_breakdown(self, base_domain):
        """Get budget breakdown by category."""
        BudgetMoveLine = self.env["budget.move.line"]
        BudgetAccount = self.env["budget.account"]
        breakdown = []

        for xml_id, name in self.BUDGET_CATEGORIES:
            # Get the budget account by XML ID
            account = self.env.ref(f"budget.{xml_id}", raise_if_not_found=False)
            if not account:
                continue

            # Filter lines by parent_path containing this account's ID
            # parent_path format: "1/2/3/" where numbers are account IDs
            category_domain = base_domain + [
                ("account_id.parent_path", "like", f"/{account.id}/"),
            ]

            # Also include lines directly on this account
            direct_domain = base_domain + [("account_id", "=", account.id)]

            # Get appropriation for this category
            appropriation_domain = [
                d for d in category_domain
            ] + [("move_id.move_type", "=", "appropriation")]
            direct_appropriation_domain = [
                d for d in direct_domain
            ] + [("move_id.move_type", "=", "appropriation")]

            category_appropriation = sum(
                BudgetMoveLine.search(appropriation_domain).mapped("balance")
            ) + sum(
                BudgetMoveLine.search(direct_appropriation_domain).mapped("balance")
            )

            # Get current balance for this category
            category_balance = sum(
                BudgetMoveLine.search(category_domain).mapped("balance")
            ) + sum(
                BudgetMoveLine.search(direct_domain).mapped("balance")
            )

            # Calculate disbursement
            category_disbursement = category_appropriation - category_balance

            breakdown.append({
                "id": account.id,
                "name": name,
                "code": account.code,
                "appropriation": category_appropriation,
                "balance": category_balance,
                "disbursement": category_disbursement,
            })

        return breakdown
