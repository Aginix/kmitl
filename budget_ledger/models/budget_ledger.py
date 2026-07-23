import logging
from collections import defaultdict

from odoo import api, models
from odoo.tools import format_date

_logger = logging.getLogger(__name__)


class BudgetLedger(models.AbstractModel):
    """Read-only service feeding the Budget Ledger (สมุดรายการเคลื่อนไหวงบประมาณ).

    The Budget Ledger opens the **main ledger** book (``budget.move.line``) as a
    chronological, line-level timeline — จัดสรร / โอน / เบิกจ่าย — with a running
    งบคงเหลือ over the filtered scope. Reservation/obligation live in a separate
    book (the encumbrance register, ``budget.commitment``) and are **not** shown
    here (ADR-0010). The Remaining (f) figure that also nets เงินจอง is surfaced
    only in the summary bar, reused verbatim from ``budget.dashboard`` — never
    re-derived in the running column (a single book cannot).

    All reads go through the ORM (never raw SQL) so ``budget_operating_unit``
    record rules scope rows to the user's operating units automatically.
    """

    _name = "budget.ledger"
    _description = "Budget Ledger (สมุดรายการเคลื่อนไหวงบประมาณ)"

    # main-ledger move types → ledger "kind". โอน (entry) is split into
    # รับโอน / โอนออก by the sign of the line balance.
    _KIND_LABELS = {
        "appropriation": "จัดสรร",
        "transfer_in": "รับโอน",
        "transfer_out": "โอนออก",
        "consume": "เบิกจ่าย",
    }
    _THAI_MONTHS = (
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
    )
    # The six financial dimensions, all stored on budget.move.line so they can
    # be filtered set-based. Source is flat (exact match); the rest hierarchical.
    _DIM_FIELDS = (
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
        "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
    )
    # Dimensions the monitoring dashboard (summary bar source) understands.
    _SUMMARY_DIM_FIELDS = (
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    @api.model
    def get_filter_options(self):
        """Options for the ControlPanel dropdowns.

        Dimension pickers list only the **top-level** analytic node of each plan
        (``parent_id = False``); the backend matches ``child_of`` so choosing a
        faculty/fund category already covers its descendants. Same guard the
        dashboard uses for the department multi-select.
        """
        analytic = self.env["account.analytic.account"]
        account = self.env["budget.account"]
        has_analytic_tree = "parent_id" in analytic._fields

        dim_plans = {
            "department_analytic_id": "departments",
            "source_analytic_id": "sources",
            "fund_analytic_id": "funds",
            "activity_analytic_id": "activities",
            "kmitl_project_analytic_id": "kmitl_project",
            "procurement_plan_analytic_id": "procurement_plan",
        }
        dims = {}
        for fname, code in dim_plans.items():
            domain = [("root_plan_id.code", "=", code)]
            if has_analytic_tree:
                domain.append(("parent_id", "=", False))
            dims[fname] = analytic.search_read(
                domain, ["id", "display_name", "code"], order="code"
            )

        acc_domain = []
        if "parent_id" in account._fields:
            acc_domain.append(("parent_id", "=", False))
        accounts = account.search_read(
            acc_domain, ["id", "display_name", "code"], order="code"
        )

        return {
            "fiscal_years": self.env["account.fiscal.year"].search_read(
                [], ["id", "name", "date_from", "date_to"], order="date_from desc"
            ),
            "dims": dims,
            "accounts": accounts,
        }

    @api.model
    def get_ledger_data(self, fiscal_year_id, options=None):
        """Return the ledger payload: summary bar + month-grouped timeline.

        ``options`` = {
            "budget_type": "expense" | "revenue"       (default "expense"),
            "filters": {<dim_field>: id | [ids], "account_id": id | [ids]},
            "kinds": ["appropriation", "transfer", "consume"]  (default all),
            "include_draft": bool                       (default False),
        }

        Draft/review rows (when ``include_draft``) are returned but excluded from
        the running งบคงเหลือ — they carry no posted accounting impact (their
        ``running`` is ``None`` and the front end greys them out).
        """
        options = options or {}
        currency_id = self.env.company.currency_id.id
        if not fiscal_year_id:
            return {"currency_id": currency_id, "summary": {}, "months": []}

        budget_type = options.get("budget_type") or "expense"
        filters = options.get("filters") or {}
        kinds = set(
            options.get("kinds") or ["appropriation", "transfer", "consume"]
        )
        include_draft = bool(options.get("include_draft"))

        domain = self._build_domain(
            fiscal_year_id, budget_type, filters, kinds, include_draft
        )
        # date-asc so the running balance accumulates from the start of the year;
        # move_name/id break ties deterministically (same order as the model).
        lines = self.env["budget.move.line"].search(
            domain, order="date asc, move_name asc, id asc"
        )
        rows = self._build_rows(lines)
        months = self._group_by_month(rows)
        return {
            "currency_id": currency_id,
            "budget_type": budget_type,
            "summary": self._summary(fiscal_year_id, budget_type, filters),
            "months": months,
            "hier_op": self._hier_op(),
        }

    # ------------------------------------------------------------------
    # domain
    # ------------------------------------------------------------------
    def _hier_op(self):
        analytic = self.env["account.analytic.account"]
        return "child_of" if "parent_id" in analytic._fields else "="

    def _build_domain(
        self, fiscal_year_id, budget_type, filters, kinds, include_draft
    ):
        domain = [
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("budget_type", "=", budget_type),
        ]
        # state: posted only unless the caller opts into draft/review.
        if include_draft:
            domain.append(("parent_state", "in", ("draft", "review", "posted")))
        else:
            domain.append(("parent_state", "=", "posted"))

        # kinds → move_type. โอน (รับโอน + โอนออก) are both move_type "entry";
        # the sign split happens per row in _classify_kind.
        move_types = []
        if "appropriation" in kinds:
            move_types.append("appropriation")
        if "transfer" in kinds:
            move_types.append("entry")
        if "consume" in kinds:
            move_types.append("consume")
        if not move_types:
            # nothing ticked → return nothing rather than everything.
            return [("id", "=", False)]
        domain.append(("move_type", "in", move_types))

        # budget account — hierarchy-aware over budget.account parent_path.
        account = filters.get("account_id")
        if account:
            acc_ids = account if isinstance(account, (list, tuple)) else [account]
            domain.append(("account_id", "child_of", acc_ids))

        # dimensions — child_of for hierarchical plans, exact/"in" for flat source.
        hier_op = self._hier_op()
        for fname in self._DIM_FIELDS:
            val = filters.get(fname)
            if not val:
                continue
            is_list = isinstance(val, (list, tuple))
            if fname == "source_analytic_id":
                op = "in" if is_list else "="
            elif is_list:
                op = "child_of" if hier_op == "child_of" else "in"
            else:
                op = hier_op
            domain.append((fname, op, val))
        return domain

    # ------------------------------------------------------------------
    # rows
    # ------------------------------------------------------------------
    def _build_rows(self, lines):
        if not lines:
            return []
        counterparties = self._transfer_counterparties(lines)
        running = 0.0
        rows = []
        for line in lines:
            balance = line.balance or 0.0
            posted = line.parent_state == "posted"
            if posted:
                running += balance
            kind = self._classify_kind(line)
            move = line.move_id
            commitment_line = move.commitment_line_id
            rows.append(
                {
                    "id": line.id,
                    "date": format_date(self.env, line.date) if line.date else "",
                    "month_key": (line.date and line.date.strftime("%Y-%m"))
                    or "unknown",
                    "kind": kind,
                    "kind_label": self._KIND_LABELS.get(kind, kind),
                    "account_code": line.account_id.code or "",
                    "account_name": line.account_id.name or "",
                    "amount": balance,
                    # running is meaningful only for posted rows; draft rows show
                    # no cumulative figure (front end greys them out).
                    "running": running if posted else None,
                    "dims": self._row_dims(line),
                    "counterparty": counterparties.get((move.id, kind), ""),
                    "move_id": move.id,
                    "move_name": line.move_name or "",
                    "ref": move.ref or "",
                    "note": line.note or "",
                    "source_model": commitment_line.res_model or "",
                    "source_id": commitment_line.res_id or False,
                    "source_name": commitment_line.res_name or "",
                    "state": line.parent_state,
                    "posted": posted,
                }
            )
        return rows

    def _classify_kind(self, line):
        move_type = line.move_type
        if move_type == "appropriation":
            return "appropriation"
        if move_type == "consume":
            return "consume"
        if move_type == "entry":
            # transfer: a positive balance is money coming IN (รับโอน), a
            # negative balance is money going OUT (โอนออก).
            return "transfer_in" if (line.balance or 0.0) >= 0 else "transfer_out"
        return move_type

    def _transfer_counterparties(self, lines):
        """Resolve the opposite-side department(s) of every transfer move.

        A รับโอน row shows "จาก <ต้นทาง>" and a โอนออก row "ไป <ปลายทาง>". The
        whole move is scanned (not just the filtered lines) so the counterparty
        still resolves when a dimension filter hides the opposite leg.
        """
        move_ids = (
            lines.filtered(lambda l: l.move_type == "entry").mapped("move_id").ids
        )
        if not move_ids:
            return {}
        by_move = defaultdict(lambda: {"in": set(), "out": set()})
        all_lines = self.env["budget.move.line"].search(
            [("move_id", "in", move_ids)]
        )
        for line in all_lines:
            dept = line.department_analytic_id.display_name
            if not dept:
                continue
            side = "in" if (line.balance or 0.0) >= 0 else "out"
            by_move[line.move_id.id][side].add(dept)
        out = {}
        for move_id, sides in by_move.items():
            # รับโอน row ← the source (out) departments; โอนออก row → the
            # destination (in) departments.
            out[(move_id, "transfer_in")] = " / ".join(sorted(sides["out"]))
            out[(move_id, "transfer_out")] = " / ".join(sorted(sides["in"]))
        return out

    def _row_dims(self, line):
        """The six dimensions as compact 'code name' labels for the row chips."""

        def label(rec):
            if not rec:
                return ""
            return ("%s %s" % (rec.code or "", rec.name or "")).strip()

        return {
            "department": label(line.department_analytic_id),
            "source": label(line.source_analytic_id),
            "fund": label(line.fund_analytic_id),
            "activity": label(line.activity_analytic_id),
            "kmitl_project": label(line.kmitl_project_analytic_id),
            "procurement_plan": label(line.procurement_plan_analytic_id),
        }

    # ------------------------------------------------------------------
    # month grouping
    # ------------------------------------------------------------------
    def _group_by_month(self, rows):
        groups = []
        index = {}
        for row in rows:
            month_key = row["month_key"]
            group = index.get(month_key)
            if group is None:
                group = {
                    "key": month_key,
                    "label": self._month_label(month_key),
                    "rows": [],
                    "debit": 0.0,
                    "credit": 0.0,
                }
                index[month_key] = group
                groups.append(group)
            group["rows"].append(row)
            amount = row["amount"]
            if amount >= 0:
                group["debit"] += amount
            else:
                group["credit"] += -amount
        return groups

    def _month_label(self, month_key):
        if not month_key or "-" not in month_key:
            return "ไม่ระบุวันที่"
        year, month = month_key.split("-")
        # Thai Buddhist-era year (พ.ศ.).
        return "%s %s" % (self._THAI_MONTHS[int(month) - 1], int(year) + 543)

    # ------------------------------------------------------------------
    # summary bar (reused from the monitoring dashboard)
    # ------------------------------------------------------------------
    def _summary(self, fiscal_year_id, budget_type, filters):
        """Snapshot from รายงานตรวจสอบงบประมาณ (``budget.dashboard``).

        Reused verbatim so the bar shows the authoritative Remaining (f) that
        also nets เงินจอง — the one figure the single-book running column cannot
        produce. The dashboard is expense-scoped, so revenue gets no encumbrance
        summary. It understands four dimensions + a single root account; project
        / procurement-plan filters (and multi-account selections) narrow the
        timeline but not this bar, which stays a best-effort context snapshot.
        """
        if budget_type != "expense":
            return {}
        dashboard = self.env["budget.dashboard"]
        dash_filters = {
            fname: filters[fname]
            for fname in self._SUMMARY_DIM_FIELDS
            if filters.get(fname)
        }
        account = filters.get("account_id")
        if isinstance(account, (list, tuple)):
            account = account[0] if len(account) == 1 else None
        data = dashboard.get_dashboard_data(
            fiscal_year_id, account or None, dash_filters
        )
        totals = defaultdict(float)
        for row in data.get("rows", []):
            if row.get("level") == 0:
                for key in ("current", "reserved", "consumed", "used", "remaining"):
                    totals[key] += row.get(key, 0.0)
        return {
            "current": totals["current"],    # (a) งบปัจจุบัน
            "reserved": totals["reserved"],  # (b) เงินจอง
            "consumed": totals["consumed"],  # (d) เบิกจ่าย
            "used": totals["used"],          # (e) รวมล็อก = Σ reserve
            "remaining": totals["remaining"],  # (f) คงเหลือ (หักจอง)
        }
