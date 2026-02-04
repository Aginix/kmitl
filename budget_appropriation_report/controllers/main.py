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

        # Collect all expense lines for dimension analysis
        all_expense_lines = all_expense_appropriations.mapped("line_ids")

        # Count distinct activities (from lines)
        expense_activities = all_expense_lines.mapped("activity_analytic_id")
        activity_count = len(expense_activities)

        # Count distinct funds (from lines)
        expense_funds = all_expense_lines.mapped("fund_analytic_id")
        fund_count = len(expense_funds)

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

        # Build activity hierarchy treemap (from lines)
        activity_treemap = self._build_line_analytic_hierarchy_treemap(
            all_expense_lines, "activity_analytic_id"
        )

        # Build fund hierarchy treemap (from lines)
        fund_treemap = self._build_line_analytic_hierarchy_treemap(
            all_expense_lines, "fund_analytic_id"
        )

        # Build sunburst data: Fund → Department → Budget Account
        sunburst_data = self._build_sunburst_data(all_expense_lines)

        # Build sankey data: Fund → Department → Budget Account
        sankey_data = self._build_sankey_data(all_expense_lines)

        # Build heatmap data: Department vs Budget Account (root level)
        heatmap_data = self._build_heatmap_data(all_expense_lines)

        # Build data table: Detailed line items
        table_data = self._build_table_data(all_expense_lines)

        # Build fund pie chart data for executive dashboard
        fund_pie_data = self._build_fund_pie_data(all_expense_lines)

        # Build account type pie chart data for executive dashboard
        account_type_pie_data = self._build_account_type_pie_data(all_expense_lines)

        # Build stacked bar chart data: Department × Account Root (percentages)
        stacked_bar_data = self._build_stacked_bar_data(all_expense_lines)

        # Build activity sankey data: Activity hierarchy (ด้าน → แผนงาน → กิจกรรม)
        activity_sankey_data = self._build_activity_sankey_data(all_expense_lines)

        # Build activity × account type table (2 levels: ด้าน/แผนงาน)
        activity_account_table = self._build_activity_account_table(all_expense_lines)

        # Build activity × fund table (2 levels: ด้าน/แผนงาน)
        activity_fund_table = self._build_activity_fund_table(all_expense_lines)

        return {
            "report_count": len(reports),
            "department_count": department_count,
            "activity_count": activity_count,
            "fund_count": fund_count,
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
            "activity_treemap": activity_treemap,
            "fund_treemap": fund_treemap,
            "sunburst_data": sunburst_data,
            "sankey_data": sankey_data,
            "heatmap_data": heatmap_data,
            "table_data": table_data,
            "fund_pie_data": fund_pie_data,
            "account_type_pie_data": account_type_pie_data,
            "stacked_bar_data": stacked_bar_data,
            "activity_sankey_data": activity_sankey_data,
            "activity_account_table": activity_account_table,
            "activity_fund_table": activity_fund_table,
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

    def _build_line_analytic_hierarchy_treemap(self, expense_lines, field_name):
        """Build hierarchy treemap for any analytic field from lines (activity, fund, etc.)."""
        analytic_data = {}

        for line in expense_lines:
            analytic = getattr(line, field_name, None)
            if not analytic:
                continue

            key = analytic.id
            if key not in analytic_data:
                analytic_data[key] = {
                    "analytic": analytic,
                    "amount": 0,
                }
            analytic_data[key]["amount"] += line.balance or 0

        return self._build_analytic_tree(analytic_data)

    def _build_analytic_tree(self, analytic_data):
        """Build FULL hierarchical tree from leaf analytics up to roots."""
        if not analytic_data:
            return []

        # Step 1: Collect all ancestors for each leaf analytic
        all_analytics = {}  # id -> analytic record
        leaf_amounts = {}  # id -> amount (only leaves have amounts)

        for ana_id, data in analytic_data.items():
            analytic = data["analytic"]
            leaf_amounts[ana_id] = data["amount"]

            # Trace up to root, collecting all ancestors
            current = analytic
            while current:
                if current.id not in all_analytics:
                    all_analytics[current.id] = current
                current = current.parent_id

        # Step 2: Create nodes for ALL analytics (including ancestors)
        nodes = {}
        for ana_id, analytic in all_analytics.items():
            nodes[ana_id] = {
                "name": analytic.name,
                "value": leaf_amounts.get(ana_id, 0),
                "children": {},
                "parent_id": analytic.parent_id.id if analytic.parent_id else None,
            }

        # Step 3: Build tree by linking children to parents
        roots = []
        for ana_id, node in nodes.items():
            parent_id = node["parent_id"]
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"][ana_id] = node
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

    def _build_sunburst_data(self, expense_lines):
        """Build sunburst data: Fund → Department → Budget Account Root (flat, 3 levels)."""
        # Group by Fund → Department → Account Root (sum up from children)
        fund_data = {}

        for line in expense_lines:
            fund = line.fund_analytic_id
            dept = line.department_analytic_id
            account = line.account_id
            amount = line.balance or 0

            if not fund or not dept or not account:
                continue

            # Get root account (traverse up to top level)
            root_account = account
            while root_account.parent_id:
                root_account = root_account.parent_id

            fund_key = fund.id
            if fund_key not in fund_data:
                fund_data[fund_key] = {
                    "name": fund.name,
                    "departments": {},
                }

            dept_key = dept.id
            if dept_key not in fund_data[fund_key]["departments"]:
                fund_data[fund_key]["departments"][dept_key] = {
                    "name": dept.name,
                    "accounts": {},
                }

            # Use root account instead of original account
            acc_key = root_account.id
            if acc_key not in fund_data[fund_key]["departments"][dept_key]["accounts"]:
                fund_data[fund_key]["departments"][dept_key]["accounts"][acc_key] = {
                    "name": root_account.display_name,
                    "value": 0,
                }
            fund_data[fund_key]["departments"][dept_key]["accounts"][acc_key]["value"] += amount

        # Convert to sunburst format
        result = []
        for fund_id, fund_info in fund_data.items():
            fund_node = {
                "name": fund_info["name"],
                "children": [],
            }
            for dept_id, dept_info in fund_info["departments"].items():
                dept_node = {
                    "name": dept_info["name"],
                    "children": [],
                }
                for acc_id, acc_info in dept_info["accounts"].items():
                    dept_node["children"].append({
                        "name": acc_info["name"],
                        "value": acc_info["value"],
                    })
                # Sort accounts by value
                dept_node["children"].sort(key=lambda x: x["value"], reverse=True)
                fund_node["children"].append(dept_node)
            # Sort departments by total value
            fund_node["children"].sort(
                key=lambda x: sum(c["value"] for c in x["children"]), reverse=True
            )
            result.append(fund_node)

        # Sort funds by total value
        result.sort(
            key=lambda x: sum(
                sum(c["value"] for c in d["children"]) for d in x["children"]
            ),
            reverse=True,
        )
        return result

    def _build_sankey_data(self, expense_lines):
        """Build sankey data: Fund → Department → Budget Account."""
        nodes_set = set()
        links = {}

        for line in expense_lines:
            fund = line.fund_analytic_id
            dept = line.department_analytic_id
            account = line.account_id
            amount = line.balance or 0

            if not fund or not dept or not account:
                continue

            # Use prefixes to ensure unique node names
            fund_name = f"กองทุน: {fund.name}"
            dept_name = f"หน่วยงาน: {dept.name}"
            acc_name = account.display_name

            nodes_set.add(fund_name)
            nodes_set.add(dept_name)
            nodes_set.add(acc_name)

            # Fund → Department link
            link_key_1 = (fund_name, dept_name)
            if link_key_1 not in links:
                links[link_key_1] = 0
            links[link_key_1] += amount

            # Department → Account link
            link_key_2 = (dept_name, acc_name)
            if link_key_2 not in links:
                links[link_key_2] = 0
            links[link_key_2] += amount

        # Convert to sankey format
        nodes = [{"name": name} for name in sorted(nodes_set)]
        links_list = [
            {"source": src, "target": tgt, "value": val}
            for (src, tgt), val in links.items()
            if val > 0
        ]

        # Sort links by value descending and limit to top 50 for performance
        links_list.sort(key=lambda x: x["value"], reverse=True)
        links_list = links_list[:100]

        # Filter nodes to only include those in links
        used_nodes = set()
        for link in links_list:
            used_nodes.add(link["source"])
            used_nodes.add(link["target"])
        nodes = [n for n in nodes if n["name"] in used_nodes]

        return {"nodes": nodes, "links": links_list}

    def _build_heatmap_data(self, expense_lines):
        """Build heatmap data: Department (rows) vs Budget Account root (columns)."""
        # Collect unique departments and root budget accounts
        dept_amounts = {}  # {dept_id: {account_root_id: amount}}
        departments = {}  # {id: name}
        account_roots = {}  # {id: name}

        for line in expense_lines:
            dept = line.department_analytic_id
            account = line.account_id
            amount = line.balance or 0

            if not dept or not account:
                continue

            # Get root account (traverse up)
            root_account = account
            while root_account.parent_id:
                root_account = root_account.parent_id

            dept_id = dept.id
            root_id = root_account.id

            if dept_id not in departments:
                departments[dept_id] = dept.name
            if root_id not in account_roots:
                account_roots[root_id] = root_account.display_name

            if dept_id not in dept_amounts:
                dept_amounts[dept_id] = {}
            if root_id not in dept_amounts[dept_id]:
                dept_amounts[dept_id][root_id] = 0
            dept_amounts[dept_id][root_id] += amount

        # Convert to heatmap format for ECharts
        # x_axis: account roots, y_axis: departments, data: [[x, y, value], ...]
        x_axis = sorted(account_roots.items(), key=lambda x: x[1])
        y_axis = sorted(departments.items(), key=lambda x: x[1])

        x_labels = [name for _, name in x_axis]
        y_labels = [name for _, name in y_axis]
        x_ids = [id for id, _ in x_axis]
        y_ids = [id for id, _ in y_axis]

        data = []
        max_value = 0
        for y_idx, dept_id in enumerate(y_ids):
            for x_idx, acc_id in enumerate(x_ids):
                value = dept_amounts.get(dept_id, {}).get(acc_id, 0)
                if value > 0:
                    data.append([x_idx, y_idx, value])
                    if value > max_value:
                        max_value = value

        return {
            "x_axis": x_labels,
            "y_axis": y_labels,
            "data": data,
            "max_value": max_value,
        }

    def _build_table_data(self, expense_lines):
        """Build detailed table data with all line items."""
        table_rows = []

        for line in expense_lines:
            dept = line.department_analytic_id
            fund = line.fund_analytic_id
            activity = line.activity_analytic_id
            account = line.account_id
            approp = line.appropriation_id

            # Get root account
            root_account = account
            while root_account and root_account.parent_id:
                root_account = root_account.parent_id

            table_rows.append({
                "id": line.id,
                "appropriation_name": approp.name if approp else "",
                "department": dept.name if dept else "",
                "fund": fund.name if fund else "",
                "activity": activity.name if activity else "",
                "account_root": root_account.display_name if root_account else "",
                "account": account.display_name if account else "",
                "amount": line.balance or 0,
            })

        # Sort by amount descending
        table_rows.sort(key=lambda x: x["amount"], reverse=True)

        return table_rows

    def _build_fund_pie_data(self, expense_lines):
        """Build pie chart data: expenses by fund."""
        fund_totals = {}
        for line in expense_lines:
            fund = line.fund_analytic_id
            if not fund:
                continue
            key = fund.id
            if key not in fund_totals:
                fund_totals[key] = {"name": fund.name, "value": 0}
            fund_totals[key]["value"] += line.balance or 0

        return sorted(fund_totals.values(), key=lambda x: x["value"], reverse=True)

    def _build_account_type_pie_data(self, expense_lines):
        """Build pie chart data: expenses by root account type."""
        account_totals = {}
        for line in expense_lines:
            account = line.account_id
            if not account:
                continue
            # Get root account
            root = account
            while root.parent_id:
                root = root.parent_id
            key = root.id
            if key not in account_totals:
                account_totals[key] = {"name": root.display_name, "value": 0}
            account_totals[key]["value"] += line.balance or 0

        return sorted(account_totals.values(), key=lambda x: x["value"], reverse=True)

    def _build_stacked_bar_data(self, expense_lines):
        """Build stacked horizontal bar: Root Department × Account Root (percentages)."""
        dept_account = {}  # {root_dept_id: {root_acc_id: amount}}
        departments = {}   # {id: name}
        account_roots = {}  # {id: name}

        for line in expense_lines:
            dept = line.department_analytic_id
            account = line.account_id
            if not dept or not account:
                continue

            # Get root department (traverse up)
            root_dept = dept
            while root_dept.parent_id:
                root_dept = root_dept.parent_id

            # Get root account (traverse up)
            root_acc = account
            while root_acc.parent_id:
                root_acc = root_acc.parent_id

            dept_id, acc_id = root_dept.id, root_acc.id

            if dept_id not in departments:
                departments[dept_id] = root_dept.name
            if acc_id not in account_roots:
                account_roots[acc_id] = root_acc.display_name

            if dept_id not in dept_account:
                dept_account[dept_id] = {}
            if acc_id not in dept_account[dept_id]:
                dept_account[dept_id][acc_id] = 0
            dept_account[dept_id][acc_id] += line.balance or 0

        # Calculate percentages
        dept_list = sorted(departments.items(), key=lambda x: x[1])
        root_list = sorted(account_roots.items(), key=lambda x: x[1])

        series = []
        for acc_id, acc_name in root_list:
            data = []
            for dept_id, _ in dept_list:
                total = sum(dept_account.get(dept_id, {}).values()) or 1
                value = dept_account.get(dept_id, {}).get(acc_id, 0)
                percentage = round(value / total * 100, 1)
                data.append(percentage)
            series.append({"name": acc_name, "data": data})

        return {
            "departments": [name for _, name in dept_list],
            "account_roots": [name for _, name in root_list],
            "series": series,
        }

    def _build_activity_sankey_data(self, expense_lines):
        """Build sankey data for activity hierarchy: ด้าน → แผนงาน → กิจกรรม."""
        # Step 1: Collect amounts per leaf activity
        leaf_amounts = {}  # {activity_id: amount}
        all_activities = {}  # {id: activity record}

        for line in expense_lines:
            activity = line.activity_analytic_id
            if not activity:
                continue

            amount = line.balance or 0
            if activity.id not in leaf_amounts:
                leaf_amounts[activity.id] = 0
            leaf_amounts[activity.id] += amount

            # Collect all ancestors
            current = activity
            while current:
                if current.id not in all_activities:
                    all_activities[current.id] = current
                current = current.parent_id

        if not leaf_amounts:
            return {"nodes": [], "links": []}

        # Step 2: Build aggregated amounts (from leaves up)
        aggregated = {}  # {id: total_amount}
        for act_id, amount in leaf_amounts.items():
            current = all_activities[act_id]
            while current:
                if current.id not in aggregated:
                    aggregated[current.id] = 0
                aggregated[current.id] += amount
                current = current.parent_id

        # Step 3: Create sankey nodes and links
        nodes_set = set()
        links = {}  # {(parent_name, child_name): amount}

        for act_id, activity in all_activities.items():
            if act_id not in aggregated or aggregated[act_id] == 0:
                continue

            # Determine level for prefix
            level = 0
            current = activity
            while current.parent_id:
                level += 1
                current = current.parent_id

            # Use level prefix for unique names
            if level == 0:
                prefix = "ด้าน: "
            elif level == 1:
                prefix = "แผนงาน: "
            else:
                prefix = "กิจกรรม: "

            node_name = f"{prefix}{activity.name}"
            nodes_set.add(node_name)

            # Create link from parent to this node
            if activity.parent_id and activity.parent_id.id in all_activities:
                parent = activity.parent_id
                parent_level = level - 1
                if parent_level == 0:
                    parent_prefix = "ด้าน: "
                elif parent_level == 1:
                    parent_prefix = "แผนงาน: "
                else:
                    parent_prefix = "กิจกรรม: "

                parent_name = f"{parent_prefix}{parent.name}"
                link_key = (parent_name, node_name)
                # Use the child's aggregated amount for the link
                links[link_key] = aggregated[act_id]

        # Convert to sankey format
        nodes = [{"name": name} for name in sorted(nodes_set)]
        links_list = [
            {"source": src, "target": tgt, "value": val}
            for (src, tgt), val in links.items()
            if val > 0
        ]

        # Sort by value and limit for performance
        links_list.sort(key=lambda x: x["value"], reverse=True)
        links_list = links_list[:150]

        # Filter nodes to only include those in links
        used_nodes = set()
        for link in links_list:
            used_nodes.add(link["source"])
            used_nodes.add(link["target"])
        nodes = [n for n in nodes if n["name"] in used_nodes]

        return {"nodes": nodes, "links": links_list}

    def _build_activity_account_table(self, expense_lines):
        """Build table: Activity (ด้าน/แผนงาน, 2 levels) × Account Type (root).

        Data is collected from deepest level and summed up, but only 2 levels displayed.
        """
        # Step 1: Collect leaf data and all ancestors
        leaf_data = {}  # {(activity_id, account_root_id): amount}
        all_activities = {}  # {id: activity record}
        account_roots = {}  # {id: name}

        for line in expense_lines:
            activity = line.activity_analytic_id
            account = line.account_id
            if not activity or not account:
                continue

            amount = line.balance or 0

            # Get root account
            root_acc = account
            while root_acc.parent_id:
                root_acc = root_acc.parent_id

            acc_id = root_acc.id
            if acc_id not in account_roots:
                account_roots[acc_id] = root_acc.display_name

            # Collect activity and all ancestors
            current = activity
            while current:
                if current.id not in all_activities:
                    all_activities[current.id] = current
                current = current.parent_id

            # Store leaf amount
            key = (activity.id, acc_id)
            if key not in leaf_data:
                leaf_data[key] = 0
            leaf_data[key] += amount

        # Step 2: Aggregate from leaves up to all ancestors
        aggregated = {}  # {(activity_id, account_id): amount}
        for (act_id, acc_id), amount in leaf_data.items():
            current = all_activities[act_id]
            while current:
                key = (current.id, acc_id)
                if key not in aggregated:
                    aggregated[key] = 0
                aggregated[key] += amount
                current = current.parent_id

        # Step 3: Determine level for each activity
        activity_levels = {}  # {id: level}
        for act_id, activity in all_activities.items():
            level = 0
            current = activity
            while current.parent_id:
                level += 1
                current = current.parent_id
            activity_levels[act_id] = level

        # Step 4: Build rows - only level 0 and level 1
        rows = []
        col_list = sorted(account_roots.items(), key=lambda x: x[1])
        columns = [{"id": id, "name": name} for id, name in col_list]

        # Get level 0 and level 1 activities
        level0_acts = {k: v for k, v in all_activities.items() if activity_levels[k] == 0}
        level1_acts = {k: v for k, v in all_activities.items() if activity_levels[k] == 1}

        for act_id, activity in sorted(level0_acts.items(), key=lambda x: x[1].name):
            row_data = {acc_id: aggregated.get((act_id, acc_id), 0) for acc_id, _ in col_list}
            row_total = sum(row_data.values())

            if row_total > 0:
                rows.append({
                    "id": act_id,
                    "name": activity.name,
                    "level": 0,
                    "data": row_data,
                    "total": row_total,
                })

                # Level 1 children
                for child_id, child_act in sorted(level1_acts.items(), key=lambda x: x[1].name):
                    if child_act.parent_id and child_act.parent_id.id == act_id:
                        child_data = {acc_id: aggregated.get((child_id, acc_id), 0) for acc_id, _ in col_list}
                        child_total = sum(child_data.values())
                        if child_total > 0:
                            rows.append({
                                "id": child_id,
                                "name": child_act.name,
                                "level": 1,
                                "data": child_data,
                                "total": child_total,
                            })

        return {"columns": columns, "rows": rows}

    def _build_activity_fund_table(self, expense_lines):
        """Build table: Activity (ด้าน/แผนงาน, 2 levels) × Fund.

        Data is collected from deepest level and summed up, but only 2 levels displayed.
        """
        # Step 1: Collect leaf data and all ancestors
        leaf_data = {}  # {(activity_id, fund_id): amount}
        all_activities = {}  # {id: activity record}
        funds = {}  # {id: name}

        for line in expense_lines:
            activity = line.activity_analytic_id
            fund = line.fund_analytic_id
            if not activity or not fund:
                continue

            amount = line.balance or 0
            fund_id = fund.id

            if fund_id not in funds:
                funds[fund_id] = fund.name

            # Collect activity and all ancestors
            current = activity
            while current:
                if current.id not in all_activities:
                    all_activities[current.id] = current
                current = current.parent_id

            # Store leaf amount
            key = (activity.id, fund_id)
            if key not in leaf_data:
                leaf_data[key] = 0
            leaf_data[key] += amount

        # Step 2: Aggregate from leaves up to all ancestors
        aggregated = {}  # {(activity_id, fund_id): amount}
        for (act_id, fund_id), amount in leaf_data.items():
            current = all_activities[act_id]
            while current:
                key = (current.id, fund_id)
                if key not in aggregated:
                    aggregated[key] = 0
                aggregated[key] += amount
                current = current.parent_id

        # Step 3: Determine level for each activity
        activity_levels = {}  # {id: level}
        for act_id, activity in all_activities.items():
            level = 0
            current = activity
            while current.parent_id:
                level += 1
                current = current.parent_id
            activity_levels[act_id] = level

        # Step 4: Build rows - only level 0 and level 1
        rows = []
        col_list = sorted(funds.items(), key=lambda x: x[1])
        columns = [{"id": id, "name": name} for id, name in col_list]

        # Get level 0 and level 1 activities
        level0_acts = {k: v for k, v in all_activities.items() if activity_levels[k] == 0}
        level1_acts = {k: v for k, v in all_activities.items() if activity_levels[k] == 1}

        for act_id, activity in sorted(level0_acts.items(), key=lambda x: x[1].name):
            row_data = {fund_id: aggregated.get((act_id, fund_id), 0) for fund_id, _ in col_list}
            row_total = sum(row_data.values())

            if row_total > 0:
                rows.append({
                    "id": act_id,
                    "name": activity.name,
                    "level": 0,
                    "data": row_data,
                    "total": row_total,
                })

                # Level 1 children
                for child_id, child_act in sorted(level1_acts.items(), key=lambda x: x[1].name):
                    if child_act.parent_id and child_act.parent_id.id == act_id:
                        child_data = {fund_id: aggregated.get((child_id, fund_id), 0) for fund_id, _ in col_list}
                        child_total = sum(child_data.values())
                        if child_total > 0:
                            rows.append({
                                "id": child_id,
                                "name": child_act.name,
                                "level": 1,
                                "data": child_data,
                                "total": child_total,
                            })

        return {"columns": columns, "rows": rows}


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
