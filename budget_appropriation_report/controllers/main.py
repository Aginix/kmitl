# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class BudgetAppropriationDashboardController(http.Controller):

    @http.route(
        "/budget_appropriation/dashboard/data",
        type="json",
        auth="user",
    )
    def get_dashboard_data(self, fiscal_year_id=None, source_id=None, **kw):
        """Get dashboard data for budget appropriation."""
        # Get fiscal years for filter options
        fiscal_years = request.env["account.fiscal.year"].search(
            [], order="date_from desc"
        )
        fiscal_year_options = [
            {"id": fy.id, "name": fy.name} for fy in fiscal_years
        ]

        # Get sources for filter options
        sources = request.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "sources")], order="code"
        )
        source_options = [
            {"id": src.id, "name": src.name, "code": src.code} for src in sources
        ]

        # Determine selected fiscal year
        if not fiscal_year_id and fiscal_years:
            fiscal_year_id = fiscal_years[0].id

        fiscal_year = None
        if fiscal_year_id:
            fy = request.env["account.fiscal.year"].browse(fiscal_year_id)
            if fy.exists():
                fiscal_year = {"id": fy.id, "name": fy.name}

        # Get dashboard statistics from budget.appropriation.report
        stats = self._get_dashboard_stats(fiscal_year_id, source_id)

        return {
            "filter_options": {
                "fiscal_years": fiscal_year_options,
                "sources": source_options,
            },
            "filters": {
                "fiscal_year_id": fiscal_year_id,
                "source_id": source_id,
            },
            "fiscal_year": fiscal_year,
            "stats": stats,
        }

    def _get_dashboard_stats(self, fiscal_year_id, source_id):
        """Calculate dashboard statistics from budget.appropriation.report."""
        domain = []
        if fiscal_year_id:
            domain.append(("account_fiscal_year_id", "=", fiscal_year_id))
        if source_id:
            domain.append(("source_analytic_id", "=", source_id))

        reports = request.env["budget.appropriation.report"].search(domain)

        # Collect all appropriations from reports
        all_revenue_appropriations = reports.mapped("revenue_appropriation_ids")
        all_expense_appropriations = reports.mapped("expense_appropriation_ids")

        # Calculate totals
        total_revenue = sum(all_revenue_appropriations.mapped("amount_total"))
        total_expense = sum(all_expense_appropriations.mapped("amount_total"))

        # Count distinct departments
        revenue_departments = all_revenue_appropriations.mapped(
            "department_analytic_id"
        )
        expense_departments = all_expense_appropriations.mapped(
            "department_analytic_id"
        )
        all_departments = revenue_departments | expense_departments
        department_count = len(all_departments)

        # Group expense by department for treemap
        department_expenses = {}
        for approp in all_expense_appropriations:
            dept = approp.department_analytic_id
            if dept:
                key = dept.id
                if key not in department_expenses:
                    department_expenses[key] = {
                        "name": dept.name,
                        "value": 0,
                    }
                department_expenses[key]["value"] += approp.amount_total

        # Sort by value descending
        treemap_data = sorted(
            department_expenses.values(), key=lambda x: x["value"], reverse=True
        )

        # Group revenue by department for treemap
        department_revenues = {}
        for approp in all_revenue_appropriations:
            dept = approp.department_analytic_id
            if dept:
                key = dept.id
                if key not in department_revenues:
                    department_revenues[key] = {
                        "name": dept.name,
                        "value": 0,
                    }
                department_revenues[key]["value"] += approp.amount_total

        # Sort by value descending
        revenue_treemap_data = sorted(
            department_revenues.values(), key=lambda x: x["value"], reverse=True
        )

        # Build hierarchical treemap: Department → Budget Account
        dept_account_treemap = self._build_department_account_treemap(
            all_expense_appropriations
        )

        # Build account-only hierarchy treemap
        account_only_treemap = self._build_account_only_treemap(
            all_expense_appropriations
        )

        return {
            "report_count": len(reports),
            "department_count": department_count,
            "total_revenue": total_revenue,
            "total_expense": total_expense,
            "pie_chart": [
                {"name": "รายรับ", "value": total_revenue},
                {"name": "รายจ่าย", "value": total_expense},
            ],
            "treemap_data": treemap_data,
            "revenue_treemap_data": revenue_treemap_data,
            "department_account_treemap": dept_account_treemap,
            "account_only_treemap": account_only_treemap,
        }

    def _build_department_account_treemap(self, expense_appropriations):
        """Build hierarchical treemap: Department hierarchy → Budget Account hierarchy."""
        # Step 1: Collect amounts per (department, account) pair
        dept_data = {}

        for approp in expense_appropriations:
            dept = approp.department_analytic_id
            if not dept:
                continue

            dept_key = dept.id
            if dept_key not in dept_data:
                dept_data[dept_key] = {
                    "department": dept,
                    "accounts": {},
                }

            for line in approp.line_ids:
                account = line.account_id
                if not account:
                    continue

                amount = line.balance or 0
                if account.id not in dept_data[dept_key]["accounts"]:
                    dept_data[dept_key]["accounts"][account.id] = {
                        "account": account,
                        "amount": 0,
                    }
                dept_data[dept_key]["accounts"][account.id]["amount"] += amount

        # Step 2: Build department hierarchy with account trees as leaves
        return self._build_dept_hierarchy(dept_data)

    def _build_dept_hierarchy(self, dept_data):
        """Build FULL department hierarchy tree with budget accounts as leaf children."""
        if not dept_data:
            return []

        # Step 1: Collect all department ancestors
        all_depts = {}  # id -> department record
        dept_accounts = {}  # id -> accounts dict (only leaf depts have data)

        for dept_id, data in dept_data.items():
            dept = data["department"]
            dept_accounts[dept_id] = data["accounts"]

            # Trace up to root, collecting all ancestors
            current = dept
            while current:
                if current.id not in all_depts:
                    all_depts[current.id] = current
                current = current.parent_id

        # Step 2: Create nodes for ALL departments (including ancestors)
        nodes = {}
        for dept_id, dept in all_depts.items():
            accounts = dept_accounts.get(dept_id, {})
            account_tree = self._build_account_tree(accounts) if accounts else []
            dept_total = sum(a["amount"] for a in accounts.values()) if accounts else 0

            nodes[dept_id] = {
                "name": dept.name,
                "value": dept_total,
                "children": {},
                "account_children": account_tree,
                "parent_id": dept.parent_id.id if dept.parent_id else None,
            }

        # Step 3: Build tree by linking children to parents
        roots = []
        for dept_id, node in nodes.items():
            parent_id = node["parent_id"]
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"][dept_id] = node
            else:
                roots.append(node)

        # Step 4: Aggregate values from leaves up to parents (bottom-up)
        def aggregate_values(node):
            total = node["value"]
            for child in node["children"].values():
                total += aggregate_values(child)
            node["value"] = total
            return total

        for root in roots:
            aggregate_values(root)

        # Step 5: Convert children dicts to sorted lists and merge account_children
        def convert_node(node):
            dept_children = list(node["children"].values())
            account_children = node.get("account_children", [])

            for child in dept_children:
                convert_node(child)

            all_children = sorted(
                dept_children + account_children,
                key=lambda x: x["value"],
                reverse=True,
            )

            if all_children:
                node["children"] = all_children
            else:
                del node["children"]

            if "account_children" in node:
                del node["account_children"]
            if "parent_id" in node:
                del node["parent_id"]

        for root in roots:
            convert_node(root)

        return sorted(roots, key=lambda x: x["value"], reverse=True)

    def _build_account_tree(self, accounts_data):
        """Build FULL hierarchical tree from leaf accounts up to roots."""
        if not accounts_data:
            return []

        # Step 1: Collect all ancestors for each leaf account
        all_accounts = {}  # id -> account record
        leaf_amounts = {}  # id -> amount (only leaves have amounts)

        for acc_id, data in accounts_data.items():
            account = data["account"]
            leaf_amounts[acc_id] = data["amount"]

            # Trace up to root, collecting all ancestors
            current = account
            while current:
                if current.id not in all_accounts:
                    all_accounts[current.id] = current
                current = current.parent_id

        # Step 2: Create nodes for ALL accounts (including ancestors)
        nodes = {}
        for acc_id, account in all_accounts.items():
            nodes[acc_id] = {
                "name": account.display_name,
                "value": leaf_amounts.get(acc_id, 0),  # Only leaves have direct values
                "children": {},
                "parent_id": account.parent_id.id if account.parent_id else None,
            }

        # Step 3: Build tree by linking children to parents
        roots = []
        for acc_id, node in nodes.items():
            parent_id = node["parent_id"]
            if parent_id and parent_id in nodes:
                # Parent exists, add as child
                nodes[parent_id]["children"][acc_id] = node
            else:
                # No parent, this is a root
                roots.append(node)

        # Step 4: Aggregate values from leaves up to parents (bottom-up)
        def aggregate_values(node):
            total = node["value"]  # Start with own value (if leaf)
            for child in node["children"].values():
                total += aggregate_values(child)
            node["value"] = total
            return total

        for root in roots:
            aggregate_values(root)

        # Step 5: Convert children dicts to sorted lists
        def convert_children(node):
            if node["children"]:
                children_list = sorted(
                    node["children"].values(),
                    key=lambda x: x["value"],
                    reverse=True,
                )
                for child in children_list:
                    convert_children(child)
                node["children"] = children_list
            else:
                del node["children"]
            if "parent_id" in node:
                del node["parent_id"]

        for root in roots:
            convert_children(root)

        return sorted(roots, key=lambda x: x["value"], reverse=True)

    def _build_account_only_treemap(self, expense_appropriations):
        """Build budget account hierarchy treemap (without departments)."""
        accounts_data = {}

        for approp in expense_appropriations:
            for line in approp.line_ids:
                account = line.account_id
                if not account:
                    continue

                amount = line.balance or 0
                if account.id not in accounts_data:
                    accounts_data[account.id] = {
                        "account": account,
                        "amount": 0,
                    }
                accounts_data[account.id]["amount"] += amount

        return self._build_account_tree(accounts_data)


class BudgetAppropriationReportController(http.Controller):

    @http.route(
        ["/budget_appropriation_report/<int:report_id>/<string:report_type>"],
        type="http",
        auth="user",
        website=True,
    )
    def budget_appropriation_report(self, report_id, report_type, **kw):
        """Render budget appropriation report in HTML or PDF format."""
        report_record = request.env["budget.appropriation.report"].browse(report_id)
        if not report_record.exists():
            return request.redirect("/web")

        if report_type == "html":
            report = request.env.ref(
                "budget_appropriation_report.action_report_budget_appropriation_report"
            )
            html = request.env["ir.actions.report"]._render_qweb_html(
                report.id, [report_record.id]
            )[0]
            return request.make_response(
                html,
                headers=[
                    ("Content-Type", "text/html"),
                    ("Content-Length", len(html)),
                ],
            )
        elif report_type == "pdf":
            report = request.env.ref(
                "budget_appropriation_report.action_report_budget_appropriation_report"
            )
            pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                report.id, [report_record.id]
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    f'inline; filename="Budget Appropriation Report - {report_record.name}.pdf"',
                ),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)

        return request.redirect("/web")
