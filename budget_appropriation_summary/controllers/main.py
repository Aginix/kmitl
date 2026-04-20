from odoo import http
from odoo.http import request


class BudgetAppropriationSummaryController(http.Controller):

    @http.route(
        "/budget_appropriation/dashboard/data",
        type="json",
        auth="user",
    )
    def get_dashboard_data(self, fiscal_year_id=None, source_id=None, **kw):
        """Get dashboard data for budget appropriation."""
        fiscal_years = request.env["account.fiscal.year"].search(
            [], order="date_from desc"
        )
        fiscal_year_options = [
            {"id": fy.id, "name": fy.name} for fy in fiscal_years
        ]
        sources = request.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "sources")], order="code"
        )
        source_options = [
            {"id": src.id, "name": src.name, "code": src.code} for src in sources
        ]
        if not fiscal_year_id and fiscal_years:
            fiscal_year_id = fiscal_years[0].id
        fiscal_year = None
        if fiscal_year_id:
            fy = request.env["account.fiscal.year"].browse(fiscal_year_id)
            if fy.exists():
                fiscal_year = {"id": fy.id, "name": fy.name}
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
        """Calculate dashboard statistics from budget.appropriation.compilation."""
        domain = []
        if fiscal_year_id:
            domain.append(("account_fiscal_year_id", "=", fiscal_year_id))
        if source_id:
            domain.append(("source_analytic_id", "=", source_id))
        compilations = request.env["budget.appropriation.compilation"].search(domain)
        all_revenue_appropriations = compilations.mapped("revenue_appropriation_ids")
        all_expense_appropriations = compilations.mapped("expense_appropriation_ids")
        total_revenue = sum(all_revenue_appropriations.mapped("amount_total"))
        total_expense = sum(all_expense_appropriations.mapped("amount_total"))
        revenue_departments = all_revenue_appropriations.mapped("department_analytic_id")
        expense_departments = all_expense_appropriations.mapped("department_analytic_id")
        all_departments = revenue_departments | expense_departments
        department_count = len(all_departments)
        all_expense_lines = all_expense_appropriations.mapped("line_ids")
        activity_count = len(all_expense_lines.mapped("activity_analytic_id"))
        fund_count = len(all_expense_lines.mapped("fund_analytic_id"))
        department_expenses = {}
        for approp in all_expense_appropriations:
            dept = approp.department_analytic_id
            if dept:
                key = dept.id
                if key not in department_expenses:
                    department_expenses[key] = {"name": dept.name, "value": 0}
                department_expenses[key]["value"] += approp.amount_total
        treemap_data = sorted(department_expenses.values(), key=lambda x: x["value"], reverse=True)
        department_revenues = {}
        for approp in all_revenue_appropriations:
            dept = approp.department_analytic_id
            if dept:
                key = dept.id
                if key not in department_revenues:
                    department_revenues[key] = {"name": dept.name, "value": 0}
                department_revenues[key]["value"] += approp.amount_total
        revenue_treemap_data = sorted(department_revenues.values(), key=lambda x: x["value"], reverse=True)
        return {
            "report_count": len(compilations),
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
            "department_account_treemap": self._build_department_account_treemap(all_expense_appropriations),
            "account_only_treemap": self._build_account_only_treemap(all_expense_appropriations),
            "activity_treemap": self._build_line_analytic_hierarchy_treemap(all_expense_lines, "activity_analytic_id"),
            "fund_treemap": self._build_line_analytic_hierarchy_treemap(all_expense_lines, "fund_analytic_id"),
            "sunburst_data": self._build_sunburst_data(all_expense_lines),
            "sankey_data": self._build_sankey_data(all_expense_lines),
            "heatmap_data": self._build_heatmap_data(all_expense_lines),
            "table_data": self._build_table_data(all_expense_lines),
            "fund_pie_data": self._build_fund_pie_data(all_expense_lines),
            "account_type_pie_data": self._build_account_type_pie_data(all_expense_lines),
            "department_pie_data": self._build_department_pie_data(all_expense_lines),
            "stacked_bar_data": self._build_stacked_bar_data(all_expense_lines),
            "activity_sankey_data": self._build_activity_sankey_data(all_expense_lines),
            "activity_account_table": self._build_activity_account_table(all_expense_lines),
            "activity_fund_table": self._build_activity_fund_table(all_expense_lines),
        }

    def _build_department_account_treemap(self, expense_appropriations):
        dept_data = {}
        for approp in expense_appropriations:
            dept = approp.department_analytic_id
            if not dept:
                continue
            dept_key = dept.id
            if dept_key not in dept_data:
                dept_data[dept_key] = {"department": dept, "accounts": {}}
            for line in approp.line_ids:
                account = line.account_id
                if not account:
                    continue
                amount = line.balance or 0
                if account.id not in dept_data[dept_key]["accounts"]:
                    dept_data[dept_key]["accounts"][account.id] = {"account": account, "amount": 0}
                dept_data[dept_key]["accounts"][account.id]["amount"] += amount
        return self._build_dept_hierarchy(dept_data)

    def _build_dept_hierarchy(self, dept_data):
        if not dept_data:
            return []
        all_depts = {}
        dept_accounts = {}
        for dept_id, data in dept_data.items():
            dept = data["department"]
            dept_accounts[dept_id] = data["accounts"]
            current = dept
            while current:
                if current.id not in all_depts:
                    all_depts[current.id] = current
                current = current.parent_id
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
        roots = []
        for dept_id, node in nodes.items():
            parent_id = node["parent_id"]
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"][dept_id] = node
            else:
                roots.append(node)

        def aggregate_values(node):
            total = node["value"]
            for child in node["children"].values():
                total += aggregate_values(child)
            node["value"] = total
            return total

        for root in roots:
            aggregate_values(root)

        def convert_node(node):
            dept_children = list(node["children"].values())
            account_children = node.get("account_children", [])
            for child in dept_children:
                convert_node(child)
            all_children = sorted(dept_children + account_children, key=lambda x: x["value"], reverse=True)
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
        if not accounts_data:
            return []
        all_accounts = {}
        leaf_amounts = {}
        for acc_id, data in accounts_data.items():
            account = data["account"]
            leaf_amounts[acc_id] = data["amount"]
            current = account
            while current:
                if current.id not in all_accounts:
                    all_accounts[current.id] = current
                current = current.parent_id
        nodes = {}
        for acc_id, account in all_accounts.items():
            nodes[acc_id] = {
                "name": account.display_name,
                "value": leaf_amounts.get(acc_id, 0),
                "children": {},
                "parent_id": account.parent_id.id if account.parent_id else None,
            }
        roots = []
        for acc_id, node in nodes.items():
            parent_id = node["parent_id"]
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"][acc_id] = node
            else:
                roots.append(node)

        def aggregate_values(node):
            total = node["value"]
            for child in node["children"].values():
                total += aggregate_values(child)
            node["value"] = total
            return total

        for root in roots:
            aggregate_values(root)

        def convert_children(node):
            if node["children"]:
                children_list = sorted(node["children"].values(), key=lambda x: x["value"], reverse=True)
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
        accounts_data = {}
        for approp in expense_appropriations:
            for line in approp.line_ids:
                account = line.account_id
                if not account:
                    continue
                amount = line.balance or 0
                if account.id not in accounts_data:
                    accounts_data[account.id] = {"account": account, "amount": 0}
                accounts_data[account.id]["amount"] += amount
        return self._build_account_tree(accounts_data)

    def _build_line_analytic_hierarchy_treemap(self, expense_lines, field_name):
        analytic_data = {}
        for line in expense_lines:
            analytic = getattr(line, field_name, None)
            if not analytic:
                continue
            key = analytic.id
            if key not in analytic_data:
                analytic_data[key] = {"analytic": analytic, "amount": 0}
            analytic_data[key]["amount"] += line.balance or 0
        return self._build_analytic_tree(analytic_data)

    def _build_analytic_tree(self, analytic_data):
        if not analytic_data:
            return []
        all_analytics = {}
        leaf_amounts = {}
        for ana_id, data in analytic_data.items():
            analytic = data["analytic"]
            leaf_amounts[ana_id] = data["amount"]
            current = analytic
            while current:
                if current.id not in all_analytics:
                    all_analytics[current.id] = current
                current = current.parent_id
        nodes = {}
        for ana_id, analytic in all_analytics.items():
            nodes[ana_id] = {
                "name": analytic.name,
                "value": leaf_amounts.get(ana_id, 0),
                "children": {},
                "parent_id": analytic.parent_id.id if analytic.parent_id else None,
            }
        roots = []
        for ana_id, node in nodes.items():
            parent_id = node["parent_id"]
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"][ana_id] = node
            else:
                roots.append(node)

        def aggregate_values(node):
            total = node["value"]
            for child in node["children"].values():
                total += aggregate_values(child)
            node["value"] = total
            return total

        for root in roots:
            aggregate_values(root)

        def convert_children(node):
            if node["children"]:
                children_list = sorted(node["children"].values(), key=lambda x: x["value"], reverse=True)
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
        fund_data = {}
        for line in expense_lines:
            fund = line.fund_analytic_id
            dept = line.department_analytic_id
            account = line.account_id
            amount = line.balance or 0
            if not fund or not dept or not account:
                continue
            root_account = account
            while root_account.parent_id:
                root_account = root_account.parent_id
            fund_key = fund.id
            if fund_key not in fund_data:
                fund_data[fund_key] = {"name": fund.name, "departments": {}}
            dept_key = dept.id
            if dept_key not in fund_data[fund_key]["departments"]:
                fund_data[fund_key]["departments"][dept_key] = {"name": dept.name, "accounts": {}}
            acc_key = root_account.id
            if acc_key not in fund_data[fund_key]["departments"][dept_key]["accounts"]:
                fund_data[fund_key]["departments"][dept_key]["accounts"][acc_key] = {"name": root_account.display_name, "value": 0}
            fund_data[fund_key]["departments"][dept_key]["accounts"][acc_key]["value"] += amount
        result = []
        for fund_id, fund_info in fund_data.items():
            fund_node = {"name": fund_info["name"], "children": []}
            for dept_id, dept_info in fund_info["departments"].items():
                dept_node = {"name": dept_info["name"], "children": []}
                for acc_id, acc_info in dept_info["accounts"].items():
                    dept_node["children"].append({"name": acc_info["name"], "value": acc_info["value"]})
                dept_node["children"].sort(key=lambda x: x["value"], reverse=True)
                fund_node["children"].append(dept_node)
            fund_node["children"].sort(key=lambda x: sum(c["value"] for c in x["children"]), reverse=True)
            result.append(fund_node)
        result.sort(key=lambda x: sum(sum(c["value"] for c in d["children"]) for d in x["children"]), reverse=True)
        return result

    def _build_sankey_data(self, expense_lines):
        nodes_set = set()
        links = {}
        for line in expense_lines:
            fund = line.fund_analytic_id
            dept = line.department_analytic_id
            account = line.account_id
            amount = line.balance or 0
            if not fund or not dept or not account:
                continue
            fund_name = f"กองทุน: {fund.name}"
            dept_name = f"หน่วยงาน: {dept.name}"
            acc_name = account.display_name
            nodes_set.add(fund_name)
            nodes_set.add(dept_name)
            nodes_set.add(acc_name)
            link_key_1 = (fund_name, dept_name)
            links[link_key_1] = links.get(link_key_1, 0) + amount
            link_key_2 = (dept_name, acc_name)
            links[link_key_2] = links.get(link_key_2, 0) + amount
        nodes = [{"name": name} for name in sorted(nodes_set)]
        links_list = [{"source": src, "target": tgt, "value": val} for (src, tgt), val in links.items() if val > 0]
        links_list.sort(key=lambda x: x["value"], reverse=True)
        links_list = links_list[:100]
        used_nodes = set()
        for link in links_list:
            used_nodes.add(link["source"])
            used_nodes.add(link["target"])
        nodes = [n for n in nodes if n["name"] in used_nodes]
        return {"nodes": nodes, "links": links_list}

    def _build_heatmap_data(self, expense_lines):
        dept_amounts = {}
        departments = {}
        account_roots = {}
        for line in expense_lines:
            dept = line.department_analytic_id
            account = line.account_id
            amount = line.balance or 0
            if not dept or not account:
                continue
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
            dept_amounts[dept_id][root_id] = dept_amounts[dept_id].get(root_id, 0) + amount
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
        return {"x_axis": x_labels, "y_axis": y_labels, "data": data, "max_value": max_value}

    def _build_table_data(self, expense_lines):
        table_rows = []
        for line in expense_lines:
            dept = line.department_analytic_id
            fund = line.fund_analytic_id
            activity = line.activity_analytic_id
            account = line.account_id
            approp = line.appropriation_id
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
        table_rows.sort(key=lambda x: x["amount"], reverse=True)
        return table_rows

    def _build_fund_pie_data(self, expense_lines):
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
        account_totals = {}
        for line in expense_lines:
            account = line.account_id
            if not account:
                continue
            root = account
            while root.parent_id:
                root = root.parent_id
            key = root.id
            if key not in account_totals:
                account_totals[key] = {"name": root.display_name, "value": 0}
            account_totals[key]["value"] += line.balance or 0
        return sorted(account_totals.values(), key=lambda x: x["value"], reverse=True)

    def _build_department_pie_data(self, expense_lines):
        dept_totals = {}
        for line in expense_lines:
            dept = line.department_analytic_id
            if not dept:
                continue
            root = dept
            while root.parent_id:
                root = root.parent_id
            key = root.id
            if key not in dept_totals:
                dept_totals[key] = {"name": root.name, "value": 0}
            dept_totals[key]["value"] += line.balance or 0
        return sorted(dept_totals.values(), key=lambda x: x["value"], reverse=True)

    def _build_stacked_bar_data(self, expense_lines):
        dept_account = {}
        departments = {}
        account_roots = {}
        for line in expense_lines:
            dept = line.department_analytic_id
            account = line.account_id
            if not dept or not account:
                continue
            root_dept = dept
            while root_dept.parent_id:
                root_dept = root_dept.parent_id
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
            dept_account[dept_id][acc_id] = dept_account[dept_id].get(acc_id, 0) + (line.balance or 0)
        dept_list = sorted(departments.items(), key=lambda x: x[1])
        root_list = sorted(account_roots.items(), key=lambda x: x[1])
        series = []
        for acc_id, acc_name in root_list:
            data = []
            for dept_id, _ in dept_list:
                total = sum(dept_account.get(dept_id, {}).values()) or 1
                value = dept_account.get(dept_id, {}).get(acc_id, 0)
                data.append(round(value / total * 100, 1))
            series.append({"name": acc_name, "data": data})
        return {"departments": [name for _, name in dept_list], "account_roots": [name for _, name in root_list], "series": series}

    def _build_activity_sankey_data(self, expense_lines):
        leaf_amounts = {}
        all_activities = {}
        for line in expense_lines:
            activity = line.activity_analytic_id
            if not activity:
                continue
            amount = line.balance or 0
            leaf_amounts[activity.id] = leaf_amounts.get(activity.id, 0) + amount
            current = activity
            while current:
                if current.id not in all_activities:
                    all_activities[current.id] = current
                current = current.parent_id
        if not leaf_amounts:
            return {"nodes": [], "links": []}
        aggregated = {}
        for act_id, amount in leaf_amounts.items():
            current = all_activities[act_id]
            while current:
                aggregated[current.id] = aggregated.get(current.id, 0) + amount
                current = current.parent_id
        nodes_set = set()
        links = {}
        for act_id, activity in all_activities.items():
            if not aggregated.get(act_id):
                continue
            level = 0
            current = activity
            while current.parent_id:
                level += 1
                current = current.parent_id
            prefix = "ด้าน: " if level == 0 else ("แผนงาน: " if level == 1 else "กิจกรรม: ")
            node_name = f"{prefix}{activity.name}"
            nodes_set.add(node_name)
            if activity.parent_id and activity.parent_id.id in all_activities:
                parent = activity.parent_id
                parent_level = level - 1
                parent_prefix = "ด้าน: " if parent_level == 0 else ("แผนงาน: " if parent_level == 1 else "กิจกรรม: ")
                parent_name = f"{parent_prefix}{parent.name}"
                links[(parent_name, node_name)] = aggregated[act_id]
        nodes = [{"name": name} for name in sorted(nodes_set)]
        links_list = [{"source": src, "target": tgt, "value": val} for (src, tgt), val in links.items() if val > 0]
        links_list.sort(key=lambda x: x["value"], reverse=True)
        links_list = links_list[:150]
        used_nodes = set()
        for link in links_list:
            used_nodes.add(link["source"])
            used_nodes.add(link["target"])
        nodes = [n for n in nodes if n["name"] in used_nodes]
        return {"nodes": nodes, "links": links_list}

    def _build_activity_account_table(self, expense_lines):
        leaf_data = {}
        all_activities = {}
        account_roots = {}
        for line in expense_lines:
            activity = line.activity_analytic_id
            account = line.account_id
            if not activity or not account:
                continue
            amount = line.balance or 0
            root_acc = account
            while root_acc.parent_id:
                root_acc = root_acc.parent_id
            acc_id = root_acc.id
            if acc_id not in account_roots:
                account_roots[acc_id] = root_acc.display_name
            current = activity
            while current:
                if current.id not in all_activities:
                    all_activities[current.id] = current
                current = current.parent_id
            key = (activity.id, acc_id)
            leaf_data[key] = leaf_data.get(key, 0) + amount
        aggregated = {}
        for (act_id, acc_id), amount in leaf_data.items():
            current = all_activities[act_id]
            while current:
                key = (current.id, acc_id)
                aggregated[key] = aggregated.get(key, 0) + amount
                current = current.parent_id
        activity_levels = {}
        for act_id, activity in all_activities.items():
            level = 0
            current = activity
            while current.parent_id:
                level += 1
                current = current.parent_id
            activity_levels[act_id] = level
        rows = []
        col_list = sorted(account_roots.items(), key=lambda x: x[1])
        columns = [{"id": id, "name": name} for id, name in col_list]
        activities_by_level = {i: {} for i in range(4)}
        for act_id, activity in all_activities.items():
            lvl = activity_levels[act_id]
            if lvl < 4:
                activities_by_level[lvl][act_id] = activity

        def add_children_account(parent_id, current_level):
            if current_level > 3:
                return
            for child_id, child_act in sorted(activities_by_level.get(current_level, {}).items(), key=lambda x: x[1].name):
                if child_act.parent_id and child_act.parent_id.id == parent_id:
                    child_data = {acc_id: aggregated.get((child_id, acc_id), 0) for acc_id, _ in col_list}
                    child_total = sum(child_data.values())
                    if child_total > 0:
                        rows.append({"id": child_id, "name": child_act.name, "level": current_level, "data": child_data, "total": child_total})
                        add_children_account(child_id, current_level + 1)

        for act_id, activity in sorted(activities_by_level[0].items(), key=lambda x: x[1].name):
            row_data = {acc_id: aggregated.get((act_id, acc_id), 0) for acc_id, _ in col_list}
            row_total = sum(row_data.values())
            if row_total > 0:
                rows.append({"id": act_id, "name": activity.name, "level": 0, "data": row_data, "total": row_total})
                add_children_account(act_id, 1)
        return {"columns": columns, "rows": rows}

    def _build_activity_fund_table(self, expense_lines):
        leaf_data = {}
        all_activities = {}
        funds = {}
        for line in expense_lines:
            activity = line.activity_analytic_id
            fund = line.fund_analytic_id
            if not activity or not fund:
                continue
            amount = line.balance or 0
            fund_id = fund.id
            if fund_id not in funds:
                funds[fund_id] = fund.name
            current = activity
            while current:
                if current.id not in all_activities:
                    all_activities[current.id] = current
                current = current.parent_id
            key = (activity.id, fund_id)
            leaf_data[key] = leaf_data.get(key, 0) + amount
        aggregated = {}
        for (act_id, fund_id), amount in leaf_data.items():
            current = all_activities[act_id]
            while current:
                key = (current.id, fund_id)
                aggregated[key] = aggregated.get(key, 0) + amount
                current = current.parent_id
        activity_levels = {}
        for act_id, activity in all_activities.items():
            level = 0
            current = activity
            while current.parent_id:
                level += 1
                current = current.parent_id
            activity_levels[act_id] = level
        rows = []
        col_list = sorted(funds.items(), key=lambda x: x[1])
        columns = [{"id": id, "name": name} for id, name in col_list]
        activities_by_level = {i: {} for i in range(4)}
        for act_id, activity in all_activities.items():
            lvl = activity_levels[act_id]
            if lvl < 4:
                activities_by_level[lvl][act_id] = activity

        def add_children_fund(parent_id, current_level):
            if current_level > 3:
                return
            for child_id, child_act in sorted(activities_by_level.get(current_level, {}).items(), key=lambda x: x[1].name):
                if child_act.parent_id and child_act.parent_id.id == parent_id:
                    child_data = {fid: aggregated.get((child_id, fid), 0) for fid, _ in col_list}
                    child_total = sum(child_data.values())
                    if child_total > 0:
                        rows.append({"id": child_id, "name": child_act.name, "level": current_level, "data": child_data, "total": child_total})
                        add_children_fund(child_id, current_level + 1)

        for act_id, activity in sorted(activities_by_level[0].items(), key=lambda x: x[1].name):
            row_data = {fid: aggregated.get((act_id, fid), 0) for fid, _ in col_list}
            row_total = sum(row_data.values())
            if row_total > 0:
                rows.append({"id": act_id, "name": activity.name, "level": 0, "data": row_data, "total": row_total})
                add_children_fund(act_id, 1)
        return {"columns": columns, "rows": rows}

    MASTER_SUMMARY_REPORT_MAP = {
        "f2": "budget_appropriation_summary.action_report_f2_revenue",
        "f4p": "budget_appropriation_summary.action_report_f4p_revenue",
        "f4w": "budget_appropriation_summary.action_report_f4w_revenue",
        "f3w_f6w": "budget_appropriation_summary.action_report_f3w_f6w_revenue",
        "f5p": "budget_appropriation_summary.action_report_f5p_expense",
        "f5w": "budget_appropriation_summary.action_report_f5w_expense",
        "f7w": "budget_appropriation_summary.action_report_f7w_expense",
        "f8w": "budget_appropriation_summary.action_report_f8w_expense",
        "f9w": "budget_appropriation_summary.action_report_f9w_expense",
        "f10w": "budget_appropriation_summary.action_report_f10w_expense",
        "f11w": "budget_appropriation_summary.action_report_f11w_expense",
    }

    @http.route(
        ["/budget_appropriation_summary/<int:summary_id>/<string:report_type>"],
        type="http",
        auth="user",
        website=True,
    )
    def budget_appropriation_summary_report(self, summary_id, report_type, **kw):
        """Render budget appropriation master summary report in HTML or PDF format."""
        record = request.env["budget.appropriation.master.summary"].browse(summary_id)
        if not record.exists():
            return request.redirect("/web")

        report = request.env.ref(
            "budget_appropriation_summary.action_report_master_summary"
        )

        if report_type == "html":
            html = request.env["ir.actions.report"]._render_qweb_html(
                report.id, [record.id], data={"title": record.name}
            )[0]
            return request.make_response(
                html,
                headers=[
                    ("Content-Type", "text/html"),
                    ("Content-Length", len(html)),
                ],
            )
        elif report_type == "pdf":
            pdf_content = record._get_merged_pdf()
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    f'inline; filename="{record.name}.pdf"',
                ),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)

        return request.redirect("/web")

    @http.route(
        [
            "/budget_appropriation_summary/<int:summary_id>"
            "/report/<string:report_name>/<string:report_type>"
        ],
        type="http",
        auth="user",
        website=True,
    )
    def budget_appropriation_summary_individual_report(
        self, summary_id, report_name, report_type, **kw
    ):
        """Render individual master summary report in HTML or PDF format."""
        record = request.env["budget.appropriation.master.summary"].browse(summary_id)
        if not record.exists():
            return request.redirect("/web")

        report_ref = self.MASTER_SUMMARY_REPORT_MAP.get(report_name)
        if not report_ref:
            return request.redirect("/web")

        report = request.env.ref(report_ref)

        if report_type == "html":
            report_env = request.env["ir.actions.report"].with_context(
                html_preview=True
            )
            html = report_env._render_qweb_html(
                report.id,
                [record.id],
                data={"title": f"{record.name} - {report_name.upper()}"},
            )[0]
            return request.make_response(
                html,
                headers=[
                    ("Content-Type", "text/html"),
                    ("Content-Length", len(html)),
                ],
            )
        elif report_type == "pdf":
            pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                report.id, [record.id]
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    f'inline; filename="{record.name} - {report_name.upper()}.pdf"',
                ),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)

        return request.redirect("/web")

    @http.route(
        [
            "/budget_appropriation_summary/compilation/<int:compilation_id>/<string:report_name>/<string:report_type>"
        ],
        type="http",
        auth="user",
        website=True,
    )
    def budget_appropriation_compilation_report(
        self, compilation_id, report_name, report_type, **kw
    ):
        """Render compilation F4/F5 report in HTML or PDF format."""
        record = request.env["budget.appropriation.compilation"].browse(compilation_id)
        if not record.exists():
            return request.redirect("/web")

        report_map = {
            "f4": "budget_appropriation_summary.action_report_compilation_f4",
            "f5": "budget_appropriation_summary.action_report_compilation_f5",
            "f23w": "budget_appropriation_summary.action_report_compilation_f23w",
        }

        report_ref = report_map.get(report_name)
        if not report_ref:
            return request.redirect("/web")

        report = request.env.ref(report_ref)

        if report_type == "html":
            report_env = request.env["ir.actions.report"].with_context(
                html_preview=True
            )
            html = report_env._render_qweb_html(
                report.id,
                [record.id],
                data={"title": f"{record.name} - {report_name.upper()}"},
            )[0]
            return request.make_response(
                html,
                headers=[
                    ("Content-Type", "text/html"),
                    ("Content-Length", len(html)),
                ],
            )
        elif report_type == "pdf":
            pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                report.id, [record.id]
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    f'inline; filename="{record.name} - {report_name.upper()}.pdf"',
                ),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)

        return request.redirect("/web")
