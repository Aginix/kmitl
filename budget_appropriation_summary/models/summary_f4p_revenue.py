import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationSummaryF4PRevenue(models.AbstractModel):
    _name = "budget.appropriation.summary.f4p.revenue"
    _description = "Budget Appropriation Summary F4-P Revenue Report"

    REVENUE_CATEGORIES = [
        ("43100 (ก)", "ค่าธรรมเนียมการศึกษา และค่าธรรมเนียมอื่น ๆ"),
        ("43300", "รายได้จากงานบริการ"),
        ("43400", "รายได้จากเงินผลประโยชน์"),
        ("43500", "รายได้จากการรับบริจาค หรือ เงินอุดหนุน"),
    ]

    # หน่วยงานรหัสนี้ (และหน่วยงานภายใต้) ให้หัก deduct เข้า 43300 แทน 43100 (ก)
    SERVICE_REVENUE_DEPT_CODE = "99"
    DEFAULT_DEDUCT_CATEGORY = "43100 (ก)"
    SERVICE_REVENUE_CATEGORY = "43300"

    @api.model
    def get_data(self, summary_id):
        summary = self.env["budget.appropriation.master.summary"].browse(summary_id)

        if not summary.exists():
            return {
                "categories": [],
                "departments": [],
                "summary": {"total_amount": 0, "compare_total_amount": 0, "diff_amount": 0, "diff_percentage": 0},
                "report": None,
                "compare_report": None,
            }

        top_level_depts = self._get_top_level_departments()
        dept_map = {d.id: {"id": d.id, "code": d.code, "name": d.name} for d in top_level_depts}

        category_dept_totals = self._build_category_dept_totals(summary, dept_map)

        compare_summary = summary.compare_summary_id
        compare_totals = {}
        if compare_summary:
            compare_totals = self._build_category_dept_totals(compare_summary, dept_map)

        categories = []
        for code, name in self.REVENUE_CATEGORIES:
            dept_totals = {}
            compare_dept_totals = {}
            for dept_id in dept_map.keys():
                key = (code, dept_id)
                if key in category_dept_totals:
                    dept_totals[dept_id] = category_dept_totals[key]
                if key in compare_totals:
                    compare_dept_totals[dept_id] = compare_totals[key]

            category_total = sum(dept_totals.values())
            compare_category_total = sum(compare_dept_totals.values())

            departments = []
            all_dept_ids = set(dept_totals.keys()) | set(compare_dept_totals.keys())
            for dept_id in all_dept_ids:
                amount = dept_totals.get(dept_id, 0)
                compare_amount = compare_dept_totals.get(dept_id, 0)

                if amount or compare_amount:
                    diff_amount = amount - compare_amount
                    diff_percentage = round((diff_amount / compare_amount) * 100, 2) if compare_amount else 0

                    departments.append({
                        **dept_map[dept_id],
                        "amount": amount,
                        "compare_amount": compare_amount,
                        "diff_amount": diff_amount,
                        "diff_percentage": diff_percentage,
                        "percentage": round((amount / category_total) * 100, 2) if category_total else 0,
                    })

            diff_cat_amount = category_total - compare_category_total
            diff_cat_percentage = round((diff_cat_amount / compare_category_total) * 100, 2) if compare_category_total else 0

            categories.append({
                "code": code,
                "name": name,
                "amount": category_total,
                "compare_amount": compare_category_total,
                "diff_amount": diff_cat_amount,
                "diff_percentage": diff_cat_percentage,
                "departments": sorted(departments, key=lambda x: x["code"]),
            })

        total_amount = sum(c["amount"] for c in categories)
        compare_total_amount = sum(c["compare_amount"] for c in categories)
        for cat in categories:
            cat["percentage"] = round((cat["amount"] / total_amount) * 100, 2) if total_amount else 0

        diff_total = total_amount - compare_total_amount
        diff_total_percentage = round((diff_total / compare_total_amount) * 100, 2) if compare_total_amount else 0

        return {
            "categories": categories,
            "departments": sorted(dept_map.values(), key=lambda x: x["code"]),
            "summary": {
                "total_amount": total_amount,
                "compare_total_amount": compare_total_amount,
                "diff_amount": diff_total,
                "diff_percentage": diff_total_percentage,
            },
            "report": {
                "id": summary.id,
                "name": summary.name,
                "fiscal_year": summary.account_fiscal_year_id.name if summary.account_fiscal_year_id else None,
                "source": summary.source_analytic_id.name if summary.source_analytic_id else None,
            },
            "compare_report": {
                "id": compare_summary.id,
                "name": compare_summary.name,
                "fiscal_year": compare_summary.account_fiscal_year_id.name if compare_summary.account_fiscal_year_id else None,
                "source": compare_summary.source_analytic_id.name if compare_summary.source_analytic_id else None,
            } if compare_summary else None,
        }

    def _build_category_dept_totals(self, summary, dept_map):
        appropriations = summary.revenue_appropriation_ids

        category_accounts = {}
        for code, _ in self.REVENUE_CATEGORIES:
            category_accounts[code] = set(self._get_accounts_in_category(code))

        totals = {}
        for line in appropriations.mapped("line_ids"):
            acc_id = line.account_id.id
            top_dept_id = self._extract_top_level_dept_id(line.department_analytic_id)

            if top_dept_id and top_dept_id in dept_map:
                for code, _ in self.REVENUE_CATEGORIES:
                    if acc_id in category_accounts[code]:
                        key = (code, top_dept_id)
                        totals[key] = totals.get(key, 0) + line.balance
                        break

        # Deduct lines do not specify activity/fund, so subtract them directly
        # from each department's revenue category cell instead of matching by
        # account. Dept "99" (and its sub-depts) deducts from 43300; others
        # deduct from 43100 (ก).
        for line in appropriations.mapped("deduct_line_ids"):
            top_dept_id = self._extract_top_level_dept_id(line.department_analytic_id)
            if top_dept_id and top_dept_id in dept_map:
                cat_code = (
                    self.SERVICE_REVENUE_CATEGORY
                    if dept_map[top_dept_id]["code"] == self.SERVICE_REVENUE_DEPT_CODE
                    else self.DEFAULT_DEDUCT_CATEGORY
                )
                key = (cat_code, top_dept_id)
                totals[key] = totals.get(key, 0) - line.balance

        return totals

    def _get_accounts_in_category(self, category_code):
        parent = self.env["budget.account"].search([
            ("code", "=", category_code),
            ("budget_type", "=", "revenue"),
        ], limit=1)

        if not parent:
            _logger.warning("Budget account with code '%s' not found", category_code)
            return []

        descendants = self.env["budget.account"].search([
            ("parent_path", "like", f"{parent.parent_path}%"),
        ])

        return descendants.ids

    def _get_top_level_departments(self):
        return self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "departments"),
            ("parent_id", "=", False),
        ], order="code ASC")

    def _extract_top_level_dept_id(self, department):
        if department and department.parent_path:
            try:
                return int(department.parent_path.split("/")[0])
            except (ValueError, IndexError):
                return None
        return None
