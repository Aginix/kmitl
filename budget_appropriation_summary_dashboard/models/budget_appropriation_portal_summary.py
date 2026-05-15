from collections import defaultdict

from odoo import api, fields, models


class BudgetAppropriationPortalSummary(models.AbstractModel):
    """Self-contained data provider for the public portal summary dashboard.

    Independent of the backend dashboard controller. All aggregation is done
    inside this model so the portal route is a thin renderer.

    The payload is organised into three namespaces (``overview``, ``revenue``,
    ``expense``) to match the three tabs on the portal page.
    """

    _name = "budget.appropriation.portal.summary"
    _description = "Budget Appropriation Portal Summary"

    # Expense root accounts that drive the category breakdown shown on the
    # dashboard. Order is significant for stacked-bar visualisations.
    EXPENSE_CATEGORY_CODES = [
        ("51000", "งบบุคลากร"),
        ("52000", "งบดำเนินงาน"),
        ("53000", "งบลงทุน"),
        ("54000", "งบเงินอุดหนุน"),
        ("55000", "งบรายจ่ายอื่น"),
        ("07020", "งบกองทุนสำรอง"),
    ]
    PERSONNEL_CATEGORY_CODE = "51000"

    # Revenue deduct lines (หักโอน / 99000) cannot be classified by category
    # because they do not carry activity/fund context. By convention they are
    # subtracted directly from this category code (matches F2/F4P/F4W reports).
    REVENUE_DEDUCT_BUCKET_CODE = "43100 (ก)"

    TOP_ITEMS_LIMIT = 15
    TOP_DEPT_LIMIT = 15
    # Cap Sankey links to keep the chart readable.
    SANKEY_LINK_LIMIT = 80

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    @api.model
    def get_summary(self, filters=None):
        """Build the full payload consumed by the portal page (HTML + JSON).

        :param dict filters: optional dict with keys:
            ``fiscal_year_id``, ``source_id``, ``department_id``.
        :returns: dict with ``filter_options``, ``filters`` (echoed back)
            and ``stats`` (overview, revenue, expense namespaces).
        """
        filters = self._normalize_filters(filters or {})
        filter_options = self._get_filter_options()
        # Defaults: latest fiscal year, first source (budget is viewed per-source).
        if not filters.get("fiscal_year_id") and filter_options["fiscal_years"]:
            filters["fiscal_year_id"] = filter_options["fiscal_years"][0]["id"]
        if not filters.get("source_id") and filter_options["sources"]:
            filters["source_id"] = filter_options["sources"][0]["id"]

        lines = self._search_lines(filters)
        stats = self._compute_stats(lines, filters)
        return {
            "filter_options": filter_options,
            "filters": filters,
            "stats": stats,
        }

    # ------------------------------------------------------------------
    # Filter handling
    # ------------------------------------------------------------------
    @api.model
    def _normalize_filters(self, filters):
        normalized = {}
        for key in (
            "fiscal_year_id",
            "department_id",
            "source_id",
        ):
            raw = filters.get(key)
            try:
                normalized[key] = int(raw) if raw not in (None, "", False) else None
            except (TypeError, ValueError):
                normalized[key] = None
        return normalized

    @api.model
    def _get_filter_options(self):
        AnalyticAccount = self.env["account.analytic.account"]
        # Restrict the year/source dropdowns to combinations that actually
        # have a master summary, otherwise a user could pick a value that
        # would always return zero rows.
        compilations = self.env["budget.appropriation.compilation"].search(
            [("master_summary_id", "!=", False)]
        )
        fiscal_years = compilations.mapped("account_fiscal_year_id").sorted(
            key=lambda fy: fy.date_from or fields.Date.today(), reverse=True
        )
        sources = compilations.mapped("source_analytic_id").sorted("code")
        # Departments level 1 = no parent
        departments = AnalyticAccount.search(
            [
                ("root_plan_id.code", "=", "departments"),
                ("parent_id", "=", False),
            ],
            order="code",
        )
        return {
            "fiscal_years": [
                {"id": fy.id, "name": fy.name} for fy in fiscal_years
            ],
            "departments": [
                {"id": d.id, "code": d.code, "name": d.name}
                for d in departments
            ],
            "sources": [
                {"id": s.id, "code": s.code, "name": s.name} for s in sources
            ],
        }

    # ------------------------------------------------------------------
    # Data fetch
    # ------------------------------------------------------------------
    @api.model
    def _search_lines(self, filters):
        """Return appropriation lines bound to a master summary.

        Only lines whose appropriation is referenced by a
        ``budget.appropriation.compilation`` attached to a
        ``budget.appropriation.master.summary`` are returned. Fiscal year
        and source filter the compilations directly; department is applied
        at the line level so sub-hierarchy filtering keeps working.
        """
        AnalyticAccount = self.env["account.analytic.account"]
        Compilation = self.env["budget.appropriation.compilation"]
        Line = self.env["budget.appropriation.line"]

        comp_domain = [("master_summary_id", "!=", False)]
        if filters.get("fiscal_year_id"):
            comp_domain.append(
                ("account_fiscal_year_id", "=", filters["fiscal_year_id"])
            )
        if filters.get("source_id"):
            comp_domain.append(
                ("source_analytic_id", "=", filters["source_id"])
            )
        compilations = Compilation.search(comp_domain)
        if not compilations:
            return Line.browse()

        appropriation_ids = list(
            set(
                compilations.mapped("revenue_appropriation_ids").ids
                + compilations.mapped("expense_appropriation_ids").ids
            )
        )
        if not appropriation_ids:
            return Line.browse()

        line_domain = [("appropriation_id", "in", appropriation_ids)]
        if filters.get("department_id"):
            dept = AnalyticAccount.browse(filters["department_id"])
            if dept.exists():
                dept_ids = AnalyticAccount.search(
                    [("parent_path", "=like", f"{dept.parent_path}%")]
                ).ids
                line_domain.append(("department_analytic_id", "in", dept_ids))
        return Line.search(line_domain)

    # ------------------------------------------------------------------
    # Aggregation orchestration
    # ------------------------------------------------------------------
    @api.model
    def _compute_stats(self, lines, filters):
        revenue_lines = lines.filtered(lambda l: l.budget_type == "revenue")
        expense_lines = lines.filtered(
            lambda l: l.budget_type == "expense" and not l.deduct
        )

        revenue_stats = self._build_revenue_stats(revenue_lines)
        expense_stats = self._build_expense_stats(expense_lines)
        kpi = {
            "total_revenue_gross": revenue_stats["totals"]["gross"],
            "total_revenue_deduct": revenue_stats["totals"]["deduct"],
            "total_revenue": revenue_stats["totals"]["net"],
            "total_expense": expense_stats["totals"]["total"],
        }
        context = self._build_context(filters)
        return {
            "kpi": kpi,
            "context": context,
            "revenue": revenue_stats,
            "expense": expense_stats,
        }

    @api.model
    def _build_context(self, filters):
        ctx = {"fiscal_year_name": "", "source_name": ""}
        if filters.get("fiscal_year_id"):
            fy = self.env["account.fiscal.year"].browse(
                filters["fiscal_year_id"]
            )
            if fy.exists():
                ctx["fiscal_year_name"] = fy.name
        if filters.get("source_id"):
            src = self.env["account.analytic.account"].browse(
                filters["source_id"]
            )
            if src.exists():
                ctx["source_name"] = src.name
        return ctx

    # ------------------------------------------------------------------
    # Revenue stats
    # ------------------------------------------------------------------
    @api.model
    def _build_revenue_stats(self, revenue_lines):
        # Per-line totals split by deduct flag
        gross = 0.0
        deduct = 0.0
        # Revenue by root account (43100 (ก), 43300, ...)
        root_totals = defaultdict(float)
        root_meta = {}
        # Per-department gross / deduct (level-1 dept on the appropriation)
        dept_gross = defaultdict(float)
        dept_deduct = defaultdict(float)
        dept_meta = {}
        # Sankey flow: source dept → deduct (recipient) dept
        flow_links = defaultdict(float)
        flow_dept_meta = {}
        # Top revenue items
        items = []
        # Dept × revenue-category matrix (non-deduct only)
        dept_cat = defaultdict(lambda: defaultdict(float))

        for line in revenue_lines:
            balance = line.balance or 0.0
            dept = line.department_analytic_id
            dept_root = self._root(dept)
            if line.deduct:
                deduct += balance
                if dept_root:
                    dept_deduct[dept_root.id] += balance
                    dept_meta[dept_root.id] = {
                        "code": dept_root.code,
                        "name": dept_root.name,
                    }
                recipient = line.deduct_analytic_id
                recipient_root = self._root(recipient)
                if dept_root and recipient_root:
                    key = (dept_root.id, recipient_root.id)
                    flow_links[key] += balance
                    flow_dept_meta[dept_root.id] = {
                        "code": dept_root.code,
                        "name": dept_root.name,
                    }
                    flow_dept_meta[recipient_root.id] = {
                        "code": recipient_root.code,
                        "name": recipient_root.name,
                    }
            else:
                gross += balance
                if dept_root:
                    dept_gross[dept_root.id] += balance
                    dept_meta[dept_root.id] = {
                        "code": dept_root.code,
                        "name": dept_root.name,
                    }
                root_account = line.account_id
                while root_account.parent_id:
                    root_account = root_account.parent_id
                if root_account:
                    root_totals[root_account.id] += balance
                    root_meta[root_account.id] = {
                        "code": root_account.code,
                        "name": root_account.name,
                    }
                if dept_root and root_account:
                    dept_cat[dept_root.id][root_account.id] += balance
            # Track top-N items regardless of deduct flag
            items.append(
                {
                    "code": line.account_id.code or "",
                    "name": line.account_id.name or "",
                    "department": dept_root.name if dept_root else "",
                    "department_code": dept_root.code if dept_root else "",
                    "is_deduct": bool(line.deduct),
                    "value": round(balance, 2),
                }
            )

        # Apply the 43100 (ก) deduct rule to revenue by category
        if deduct:
            bucket = self.env["budget.account"].search(
                [("code", "=", self.REVENUE_DEDUCT_BUCKET_CODE)],
                limit=1,
            )
            if bucket:
                root_totals[bucket.id] = (
                    root_totals.get(bucket.id, 0.0) - deduct
                )
                root_meta.setdefault(
                    bucket.id,
                    {"code": bucket.code, "name": bucket.name},
                )

        by_category = sorted(
            [
                {
                    "name": root_meta[rid]["name"],
                    "code": root_meta[rid]["code"],
                    "value": round(amt, 2),
                }
                for rid, amt in root_totals.items()
                if amt
            ],
            key=lambda x: x["value"],
            reverse=True,
        )

        # Per-department gross/net (sorted by gross desc)
        per_department = sorted(
            [
                {
                    "id": did,
                    "code": dept_meta[did]["code"],
                    "name": dept_meta[did]["name"],
                    "gross": round(dept_gross.get(did, 0.0), 2),
                    "deduct": round(dept_deduct.get(did, 0.0), 2),
                    "net": round(
                        dept_gross.get(did, 0.0) - dept_deduct.get(did, 0.0),
                        2,
                    ),
                }
                for did in set(dept_gross) | set(dept_deduct)
            ],
            key=lambda x: x["gross"],
            reverse=True,
        )

        # Sankey: nodes + links
        sankey_nodes = []
        sankey_links = []
        if flow_links:
            # Add a "src:" prefix to source nodes and "dst:" to destination
            # nodes to avoid collisions when the same dept appears on both
            # sides of a transfer.
            for did, meta in flow_dept_meta.items():
                pass
            # Build node lists
            src_ids = {key[0] for key in flow_links}
            dst_ids = {key[1] for key in flow_links}
            node_index = {}
            for did in sorted(src_ids):
                meta = flow_dept_meta[did]
                name = f"[{meta['code']}] {meta['name']} (ต้นทาง)"
                node_index[("src", did)] = len(sankey_nodes)
                sankey_nodes.append({"name": name})
            for did in sorted(dst_ids):
                meta = flow_dept_meta[did]
                name = f"[{meta['code']}] {meta['name']} (ปลายทาง)"
                node_index[("dst", did)] = len(sankey_nodes)
                sankey_nodes.append({"name": name})
            for (src_id, dst_id), amount in flow_links.items():
                if not amount:
                    continue
                sankey_links.append(
                    {
                        "source": sankey_nodes[node_index[("src", src_id)]][
                            "name"
                        ],
                        "target": sankey_nodes[node_index[("dst", dst_id)]][
                            "name"
                        ],
                        "value": round(amount, 2),
                    }
                )

        items.sort(key=lambda x: x["value"], reverse=True)
        top_items = items[: self.TOP_ITEMS_LIMIT]

        # Dept × revenue-category heatmap (top depts only, all 43xxx categories)
        dept_category_heatmap = self._build_dept_revenue_heatmap(
            dept_cat, dept_meta, root_meta, by_category
        )

        return {
            "totals": {
                "gross": round(gross, 2),
                "deduct": round(deduct, 2),
                "net": round(gross - deduct, 2),
            },
            "by_category": by_category,
            "per_department": per_department,
            "deduct_flow": {"nodes": sankey_nodes, "links": sankey_links},
            "dept_category_heatmap": dept_category_heatmap,
            "top_items": top_items,
        }

    @api.model
    def _build_dept_revenue_heatmap(self, dept_cat, dept_meta, root_meta, by_category):
        """Build a heatmap where columns are revenue categories and rows are
        level-1 departments (top 15 by total non-deduct revenue)."""
        if not dept_cat or not by_category:
            return {"x": [], "y": [], "data": [], "max": 0}
        # Use the sorted by_category order so column order matches the donut
        # (largest categories on the left).
        cat_order = [c["code"] for c in by_category]
        code_to_root_id = {meta["code"]: rid for rid, meta in root_meta.items()}
        # Pick top departments by their total revenue contribution
        dept_totals = [
            (did, sum(cats.values())) for did, cats in dept_cat.items()
        ]
        dept_totals.sort(key=lambda t: t[1], reverse=True)
        top_depts = [did for did, _ in dept_totals[: self.TOP_DEPT_LIMIT]]
        x_labels = [c["name"] for c in by_category]
        y_labels = [
            f"[{dept_meta[did]['code']}] {dept_meta[did]['name']}"
            for did in top_depts
        ]
        data = []
        max_value = 0.0
        for y_idx, did in enumerate(top_depts):
            for x_idx, code in enumerate(cat_order):
                rid = code_to_root_id.get(code)
                value = dept_cat[did].get(rid, 0.0) if rid else 0.0
                if value:
                    rounded = round(value, 2)
                    data.append([x_idx, y_idx, rounded])
                    if rounded > max_value:
                        max_value = rounded
        return {
            "x": x_labels,
            "y": y_labels,
            "data": data,
            "max": max_value,
        }

    # ------------------------------------------------------------------
    # Expense stats
    # ------------------------------------------------------------------
    @api.model
    def _build_expense_stats(self, expense_lines):
        cat_lookup = self._expense_category_lookup()
        category_label_map = dict(self.EXPENSE_CATEGORY_CODES)

        total = 0.0
        category_totals = defaultdict(float)
        dept_amounts = defaultdict(lambda: defaultdict(float))
        dept_meta = {}
        fund_totals = defaultdict(float)
        fund_meta = {}
        activity_totals = defaultdict(float)
        activity_meta = {}
        items = []
        # 3-stage Sankey: (fund_root, dept_root) and (dept_root, cat_code)
        sankey_fund_dept = defaultdict(float)
        sankey_dept_cat = defaultdict(float)
        # Dept × Activity (level-1) heatmap
        dept_activity_l1 = defaultdict(lambda: defaultdict(float))
        activity_l1_meta = {}
        # Activity sunburst: nested {l0_id: {l1_id: {l2_id: amount}}}
        sunburst_amounts = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )
        activity_node_meta = {}

        for line in expense_lines:
            balance = line.balance or 0.0
            total += balance
            cat_key = cat_lookup.get(line.account_id.id)
            dept_root = self._root(line.department_analytic_id)
            fund_root = self._root(line.fund_analytic_id)
            activity_root = self._root(line.activity_analytic_id)
            activity_chain = self._ancestor_chain(line.activity_analytic_id)
            if dept_root and cat_key:
                dept_amounts[dept_root.id][cat_key] += balance
                dept_meta[dept_root.id] = {
                    "code": dept_root.code,
                    "name": dept_root.name,
                }
                category_totals[cat_key] += balance
                # Stage 2 of Sankey: dept → category
                sankey_dept_cat[(dept_root.id, cat_key)] += balance
            if fund_root:
                fund_totals[fund_root.id] += balance
                fund_meta[fund_root.id] = {
                    "code": fund_root.code,
                    "name": fund_root.name,
                }
            if activity_root:
                activity_totals[activity_root.id] += balance
                activity_meta[activity_root.id] = {
                    "code": activity_root.code,
                    "name": activity_root.name,
                }
            if dept_root and fund_root:
                # Stage 1 of Sankey: fund → dept
                sankey_fund_dept[(fund_root.id, dept_root.id)] += balance
            # Dept × Activity level-1 (แผนงาน). If the line's activity
            # is at level 0 (just a ด้าน without แผนงาน), fall back to
            # using level 0 as the column.
            if dept_root and activity_chain:
                l1 = activity_chain[1] if len(activity_chain) > 1 else activity_chain[0]
                dept_activity_l1[dept_root.id][l1.id] += balance
                activity_l1_meta[l1.id] = {
                    "code": l1.code,
                    "name": l1.name,
                }
            # Sunburst: level 0 → level 1 → level 2
            if activity_chain:
                l0 = activity_chain[0]
                l1 = activity_chain[1] if len(activity_chain) > 1 else None
                l2 = activity_chain[2] if len(activity_chain) > 2 else None
                if l0 and l1 and l2:
                    sunburst_amounts[l0.id][l1.id][l2.id] += balance
                elif l0 and l1:
                    sunburst_amounts[l0.id][l1.id][None] += balance
                elif l0:
                    sunburst_amounts[l0.id][None][None] += balance
                for node in (l0, l1, l2):
                    if node:
                        activity_node_meta[node.id] = {
                            "code": node.code,
                            "name": node.name,
                        }
            items.append(
                {
                    "code": line.account_id.code or "",
                    "name": line.account_id.name or "",
                    "department": dept_root.name if dept_root else "",
                    "department_code": dept_root.code if dept_root else "",
                    "fund": fund_root.name if fund_root else "",
                    "value": round(balance, 2),
                }
            )

        by_category = [
            {
                "name": category_label_map[code],
                "code": code,
                "value": round(category_totals.get(code, 0.0), 2),
            }
            for code, _label in self.EXPENSE_CATEGORY_CODES
            if category_totals.get(code)
        ]

        dept_totals = [
            {
                "id": did,
                "code": dept_meta[did]["code"],
                "name": dept_meta[did]["name"],
                "value": round(sum(cats.values()), 2),
                "breakdown": {
                    code: round(cats.get(code, 0.0), 2)
                    for code, _ in self.EXPENSE_CATEGORY_CODES
                },
            }
            for did, cats in dept_amounts.items()
        ]
        dept_totals.sort(key=lambda x: x["value"], reverse=True)

        # Personnel-vs-other stacked bar per dept (uses category code 51000)
        personnel_ratio = []
        for dept in dept_totals:
            personnel = dept["breakdown"].get(self.PERSONNEL_CATEGORY_CODE, 0.0)
            other = dept["value"] - personnel
            personnel_ratio.append(
                {
                    "id": dept["id"],
                    "code": dept["code"],
                    "name": dept["name"],
                    "personnel": round(personnel, 2),
                    "other": round(other, 2),
                    "total": dept["value"],
                    "pct_personnel": round(
                        personnel / dept["value"] * 100, 1
                    )
                    if dept["value"]
                    else 0.0,
                }
            )

        heatmap = self._build_heatmap(dept_totals)

        fund_pie = sorted(
            [
                {
                    "name": fund_meta[fid]["name"],
                    "code": fund_meta[fid]["code"],
                    "value": round(amt, 2),
                }
                for fid, amt in fund_totals.items()
                if amt
            ],
            key=lambda x: x["value"],
            reverse=True,
        )
        activity_bar = sorted(
            [
                {
                    "name": activity_meta[aid]["name"],
                    "code": activity_meta[aid]["code"],
                    "value": round(amt, 2),
                }
                for aid, amt in activity_totals.items()
                if amt
            ],
            key=lambda x: x["value"],
            reverse=True,
        )

        items.sort(key=lambda x: x["value"], reverse=True)
        top_items = items[: self.TOP_ITEMS_LIMIT]

        # Concentration: share captured by top-5 departments
        sorted_totals = sorted(
            (d["value"] for d in dept_totals), reverse=True
        )
        top5 = sum(sorted_totals[:5])
        concentration_pct = round(top5 / total * 100, 1) if total else 0.0

        # 3-stage Sankey: fund → dept → category
        fund_dept_cat_sankey = self._build_fund_dept_cat_sankey(
            sankey_fund_dept,
            sankey_dept_cat,
            fund_meta,
            dept_meta,
            category_label_map,
        )
        # Dept × Activity-level-1 heatmap
        dept_activity_heatmap = self._build_dept_activity_heatmap(
            dept_activity_l1, dept_meta, activity_l1_meta
        )
        # Activity sunburst (3 levels: ด้าน → แผนงาน → กิจกรรมหลัก)
        activity_sunburst = self._build_activity_sunburst(
            sunburst_amounts, activity_node_meta
        )

        return {
            "totals": {"total": round(total, 2)},
            "by_category": by_category,
            "department_bar": dept_totals[: self.TOP_DEPT_LIMIT],
            "department_table": dept_totals,
            "fund_pie": fund_pie,
            "activity_bar": activity_bar,
            "heatmap": heatmap,
            "personnel_ratio": personnel_ratio,
            "top_items": top_items,
            "categories": [
                {"code": code, "name": label}
                for code, label in self.EXPENSE_CATEGORY_CODES
            ],
            "concentration": {
                "top5_pct": concentration_pct,
                "total_dept_count": len(dept_totals),
            },
            "fund_dept_cat_sankey": fund_dept_cat_sankey,
            "dept_activity_heatmap": dept_activity_heatmap,
            "activity_sunburst": activity_sunburst,
        }

    @api.model
    def _build_fund_dept_cat_sankey(
        self, fund_dept, dept_cat, fund_meta, dept_meta, category_label_map
    ):
        """Build 3-stage Sankey: fund → department → expense category.

        Each set of links is built independently from the raw aggregates so
        the chart respects the per-edge totals. Edges are capped at
        ``SANKEY_LINK_LIMIT`` per stage (largest values kept).
        """
        if not fund_dept or not dept_cat:
            return {"nodes": [], "links": []}

        fund_label = lambda fid: f"กองทุน: [{fund_meta[fid]['code']}] {fund_meta[fid]['name']}"
        dept_label = lambda did: f"หน่วยงาน: [{dept_meta[did]['code']}] {dept_meta[did]['name']}"
        cat_label = lambda code: f"หมวด: [{code}] {category_label_map.get(code, code)}"

        # Stage 1: keep top-N links by value
        s1 = sorted(fund_dept.items(), key=lambda kv: kv[1], reverse=True)[
            : self.SANKEY_LINK_LIMIT
        ]
        s2 = sorted(dept_cat.items(), key=lambda kv: kv[1], reverse=True)[
            : self.SANKEY_LINK_LIMIT
        ]
        node_names = set()
        for (fid, did), _ in s1:
            node_names.add(fund_label(fid))
            node_names.add(dept_label(did))
        for (did, code), _ in s2:
            node_names.add(dept_label(did))
            node_names.add(cat_label(code))

        nodes = [{"name": n} for n in sorted(node_names)]
        links = []
        for (fid, did), amount in s1:
            if amount:
                links.append(
                    {
                        "source": fund_label(fid),
                        "target": dept_label(did),
                        "value": round(amount, 2),
                    }
                )
        for (did, code), amount in s2:
            if amount:
                links.append(
                    {
                        "source": dept_label(did),
                        "target": cat_label(code),
                        "value": round(amount, 2),
                    }
                )
        return {"nodes": nodes, "links": links}

    @api.model
    def _build_dept_activity_heatmap(
        self, dept_activity_l1, dept_meta, activity_l1_meta
    ):
        """Heatmap: rows = top departments, columns = activity level-1 (แผนงาน)."""
        if not dept_activity_l1 or not activity_l1_meta:
            return {"x": [], "y": [], "data": [], "max": 0}
        # Sort columns by descending total to put the bigger programs first
        activity_totals = defaultdict(float)
        for cats in dept_activity_l1.values():
            for aid, amt in cats.items():
                activity_totals[aid] += amt
        col_ids = sorted(
            activity_l1_meta.keys(),
            key=lambda aid: activity_totals[aid],
            reverse=True,
        )
        x_labels = [activity_l1_meta[aid]["name"] for aid in col_ids]
        # Rows: top departments by total
        dept_totals_local = [
            (did, sum(cats.values()))
            for did, cats in dept_activity_l1.items()
        ]
        dept_totals_local.sort(key=lambda t: t[1], reverse=True)
        row_ids = [did for did, _ in dept_totals_local[: self.TOP_DEPT_LIMIT]]
        y_labels = [
            f"[{dept_meta[did]['code']}] {dept_meta[did]['name']}"
            for did in row_ids
        ]
        data = []
        max_value = 0.0
        for y_idx, did in enumerate(row_ids):
            for x_idx, aid in enumerate(col_ids):
                value = dept_activity_l1[did].get(aid, 0.0)
                if value:
                    rounded = round(value, 2)
                    data.append([x_idx, y_idx, rounded])
                    if rounded > max_value:
                        max_value = rounded
        return {
            "x": x_labels,
            "y": y_labels,
            "data": data,
            "max": max_value,
        }

    @api.model
    def _build_activity_sunburst(self, sunburst_amounts, node_meta):
        """Build nested ECharts sunburst data with up to 3 rings.

        Drops the synthetic ``None`` sentinel used for lines that stop at
        level 0/1, but their amount still flows up to the parent ring.
        """
        if not sunburst_amounts:
            return []
        result = []
        for l0_id, l1_map in sunburst_amounts.items():
            l0_children = []
            for l1_id, l2_map in l1_map.items():
                if l1_id is None:
                    # amount stays at level 0 — represented by a leaf child
                    leaf_amount = l2_map.get(None, 0.0)
                    if leaf_amount:
                        l0_children.append(
                            {"name": "(ไม่ระบุแผนงาน)", "value": round(leaf_amount, 2)}
                        )
                    continue
                meta_l1 = node_meta.get(l1_id, {})
                l1_children = []
                for l2_id, amount in l2_map.items():
                    if l2_id is None:
                        if amount:
                            l1_children.append(
                                {
                                    "name": "(ไม่ระบุกิจกรรมหลัก)",
                                    "value": round(amount, 2),
                                }
                            )
                        continue
                    meta_l2 = node_meta.get(l2_id, {})
                    if amount:
                        l1_children.append(
                            {
                                "name": meta_l2.get("name", "?"),
                                "value": round(amount, 2),
                            }
                        )
                l0_children.append(
                    {
                        "name": meta_l1.get("name", "?"),
                        "children": l1_children,
                    }
                )
            meta_l0 = node_meta.get(l0_id, {})
            result.append(
                {
                    "name": meta_l0.get("name", "?"),
                    "children": l0_children,
                }
            )
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _expense_category_lookup(self):
        """Map every expense account id to its root category code.

        Looks up the five expense roots plus the reserve fund root once,
        then walks ``parent_path`` to bucket descendants. Builds a single
        dict so per-line lookups stay O(1).
        """
        BudgetAccount = self.env["budget.account"]
        codes = [c for c, _ in self.EXPENSE_CATEGORY_CODES]
        roots = BudgetAccount.search([("code", "in", codes)])
        if not roots:
            return {}
        root_path_to_code = {r.parent_path: r.code for r in roots}
        descendants = BudgetAccount.search(
            ["|"] * (len(roots) - 1)
            + [
                ("parent_path", "=like", f"{r.parent_path}%") for r in roots
            ]
        )
        lookup = {}
        for desc in descendants:
            for path, code in root_path_to_code.items():
                if desc.parent_path.startswith(path):
                    lookup[desc.id] = code
                    break
        return lookup

    @staticmethod
    def _root(record):
        cur = record
        while cur and cur.parent_id:
            cur = cur.parent_id
        return cur or None

    @staticmethod
    def _ancestor_chain(record):
        """Return ancestors top-down: [level_0, level_1, ..., record]."""
        chain = []
        cur = record
        while cur:
            chain.append(cur)
            cur = cur.parent_id
        chain.reverse()
        return chain

    @api.model
    def _build_heatmap(self, dept_totals):
        if not dept_totals:
            return {"x": [], "y": [], "data": [], "max": 0}
        depts = [d for d in dept_totals if d["value"]]
        x_codes = [c for c, _ in self.EXPENSE_CATEGORY_CODES]
        x_labels = [label for _, label in self.EXPENSE_CATEGORY_CODES]
        y_labels = [
            f"[{d['code']}] {d['name']}" if d.get("code") else d["name"]
            for d in depts
        ]
        data = []
        max_value = 0.0
        for y_idx, dept in enumerate(depts):
            for x_idx, code in enumerate(x_codes):
                value = dept["breakdown"].get(code, 0.0)
                if value:
                    data.append([x_idx, y_idx, value])
                    if value > max_value:
                        max_value = value
        return {
            "x": x_labels,
            "y": y_labels,
            "data": data,
            "max": max_value,
        }
