import logging
from collections import Counter
from urllib.parse import urlencode

import pytz

from odoo import http
from odoo.http import request

from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

# Sources rolled up into the two public columns: codes 1/3/5 are แผ่นดิน
# (incl. งบกลาง and เงินกันเหลื่อมปี); every other source counts as เงินรายได้.
GOV_SOURCE_CODES = ("1", "3", "5")

# Public-facing workflow states, in order (draft and cancel are never shown).
PUBLIC_STATES = [
    ("to_verify", "รอจัดสรรงบประมาณ"),
    ("verified", "รอดำเนินการ"),
    ("in_progress", "กำลังดำเนินการ"),
    ("done", "เสร็จสิ้น"),
]

THAI_MONTHS = [
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
]
THAI_MONTHS_SHORT = [
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
]

PLANS_PER_PAGE = 20


def th_date(value, with_time=False):
    """Format a date/datetime as a Thai Buddhist-era date (e.g. 12 ก.ย. 2569)."""
    if not value:
        return "-"
    if with_time:
        tz = pytz.timezone(request.env.user.tz or "Asia/Bangkok")
        value = pytz.utc.localize(value).astimezone(tz)
    res = "%s %s %s" % (value.day, THAI_MONTHS_SHORT[value.month - 1], value.year + 543)
    if with_time:
        res += " เวลา %s น." % value.strftime("%H:%M")
    return res


def fmt_amount(value, digits=0):
    return "{:,.{d}f}".format(value or 0.0, d=digits)


def fmt_million(value):
    res = "{:,.1f}".format((value or 0.0) / 1e6)
    return res[:-2] if res.endswith(".0") else res


class ProcurementPlanPortal(http.Controller):
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_fiscal_years(self, fiscal_year_id):
        """Return (all fiscal years, selected one); default to the latest."""
        fiscal_years = (
            request.env["account.fiscal.year"].sudo().search([], order="date_from desc")
        )
        current_fy = fiscal_years[:1]
        if fiscal_year_id and str(fiscal_year_id).isdigit():
            current_fy = (
                fiscal_years.filtered(lambda fy: fy.id == int(fiscal_year_id))
                or current_fy
            )
        return fiscal_years, current_fy

    def _get_root_department(self, department_code):
        departments_plan = request.env.ref(
            "account_analytic_kmitl.analytic_plan_departments"
        )
        return (
            request.env["account.analytic.account"]
            .sudo()
            .search(
                [
                    ("plan_id", "=", departments_plan.id),
                    ("parent_id", "=", False),
                    ("code", "=", department_code),
                ],
                limit=1,
            )
        )

    def _get_gov_source_ids(self):
        """Ids of the แผ่นดิน sources; every other source counts as เงินรายได้."""
        sources_plan = request.env.ref("account_analytic_kmitl.analytic_plan_sources")
        return (
            request.env["account.analytic.account"]
            .sudo()
            .search(
                [("plan_id", "=", sources_plan.id), ("code", "in", GOV_SOURCE_CODES)]
            )
            .ids
        )

    def _plan_domain(self, current_fy, department=None):
        domain = [("state", "in", [s for s, _label in PUBLIC_STATES])]
        if department:
            domain.append(("department_analytic_id", "child_of", department.id))
        if current_fy:
            domain.append(("account_fiscal_year_id", "=", current_fy.id))
        return domain

    def _source_domain(self, source, gov_ids):
        if source == "gov":
            return [("source_analytic_id", "in", gov_ids)]
        if source == "rev":
            return [("source_analytic_id", "not in", gov_ids)]
        return []

    def _state_counts(self, domain):
        Plan = request.env["procurement.plan"].sudo()
        groups = Plan.read_group(domain, ["state"], ["state"], lazy=False)
        return {g["state"]: g["__count"] for g in groups}

    def _fiscal_months(self, fiscal_year):
        """The 12 months of the fiscal year, in order, as
        [(month selection key, short label, full label)] with BE years."""
        start = fiscal_year.date_from
        months = []
        for i in range(12):
            m = (start.month - 1 + i) % 12 + 1
            y = start.year + (start.month - 1 + i) // 12 + 543
            months.append(
                (
                    str(m),
                    "%s %s" % (THAI_MONTHS_SHORT[m - 1], str(y)[-2:]),
                    "%s %s" % (THAI_MONTHS[m - 1], y),
                )
            )
        return months

    def _common_values(self, fiscal_years, current_fy):
        return {
            "fiscal_years": fiscal_years,
            "current_fy": current_fy,
            "public_states": PUBLIC_STATES,
            "state_labels": dict(PUBLIC_STATES),
            "th_date": th_date,
            "fmt_amount": fmt_amount,
            "fmt_million": fmt_million,
            "is_internal": request.env.user.has_group("base.group_user"),
        }

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    @http.route("/procurement-plans", type="http", auth="public", website=True)
    def overview(self, fiscal_year_id=None, **kw):
        Plan = request.env["procurement.plan"].sudo()
        fiscal_years, current_fy = self._get_fiscal_years(fiscal_year_id)
        gov_ids = self._get_gov_source_ids()
        domain = self._plan_domain(current_fy) + [
            ("department_analytic_id", "!=", False)
        ]

        departments_plan = request.env.ref(
            "account_analytic_kmitl.analytic_plan_departments"
        )
        root_departments = (
            request.env["account.analytic.account"]
            .sudo()
            .search(
                [("plan_id", "=", departments_plan.id), ("parent_id", "=", False)],
                order="code",
            )
        )
        rows = {
            dept.id: {"dept": dept, "count": 0, "gov": 0.0, "rev": 0.0}
            for dept in root_departments
        }

        # One grouped query, rolled up to the root department via parent_path
        groups = Plan.read_group(
            domain,
            ["total_price:sum"],
            ["department_analytic_id", "source_analytic_id"],
            lazy=False,
        )
        dept_ids = [
            g["department_analytic_id"][0]
            for g in groups
            if g["department_analytic_id"]
        ]
        root_of = {
            d.id: int(d.parent_path.split("/")[0])
            for d in request.env["account.analytic.account"].sudo().browse(dept_ids)
        }
        for g in groups:
            dept = g["department_analytic_id"]
            row = dept and rows.get(root_of.get(dept[0]))
            if not row:
                continue
            source = g["source_analytic_id"]
            key = "gov" if source and source[0] in gov_ids else "rev"
            row["count"] += g["__count"]
            row[key] += g["total_price"]

        dept_rows = [r for r in rows.values() if r["count"]]
        totals = {
            "count": sum(r["count"] for r in dept_rows),
            "gov": sum(r["gov"] for r in dept_rows),
            "rev": sum(r["rev"] for r in dept_rows),
        }
        totals["total"] = totals["gov"] + totals["rev"]

        values = self._common_values(fiscal_years, current_fy)
        values.update(
            {
                "dept_rows": dept_rows,
                "totals": totals,
                "state_counts": self._state_counts(domain),
                "last_update": Plan.search(
                    domain, order="write_date desc", limit=1
                ).write_date,
            }
        )
        return request.render(
            "procurement_plan_portal.portal_procurement_plans", values
        )

    @http.route(
        [
            "/procurement-plans/<string:department_code>",
            "/procurement-plans/<string:department_code>/page/<int:page>",
        ],
        type="http",
        auth="public",
        website=True,
    )
    def department_detail(
        self,
        department_code,
        page=1,
        fiscal_year_id=None,
        source=None,
        state=None,
        search=None,
        **kw,
    ):
        Plan = request.env["procurement.plan"].sudo()
        dept = self._get_root_department(department_code)
        if not dept:
            return request.redirect("/procurement-plans")

        fiscal_years, current_fy = self._get_fiscal_years(fiscal_year_id)
        gov_ids = self._get_gov_source_ids()
        base_domain = self._plan_domain(current_fy, dept)

        # Summary (always unfiltered within the department)
        all_plans = Plan.search(base_domain)
        gov_plans = all_plans.filtered(lambda p: p.source_analytic_id.id in gov_ids)
        total = sum(all_plans.mapped("total_price"))
        gov_total = sum(gov_plans.mapped("total_price"))
        actual = sum(-p.analytic_account_balance for p in all_plans)
        methods = Counter(
            p.procurement_method_id.name or "ไม่ระบุ" for p in all_plans
        ).most_common()

        # Filters
        source = source if source in ("gov", "rev") else "all"
        state = state if state in dict(PUBLIC_STATES) else "all"
        search = (search or "").strip()
        filter_domain = base_domain + self._source_domain(source, gov_ids)
        if search:
            filter_domain += [
                "|",
                ("name", "ilike", search),
                ("description", "ilike", search),
            ]
        state_counts = self._state_counts(filter_domain)
        if state != "all":
            filter_domain += [("state", "=", state)]

        def query(**overrides):
            args = {
                "fiscal_year_id": current_fy.id,
                "source": source,
                "state": state,
                "search": search,
                **overrides,
            }
            return {k: v for k, v in args.items() if v and v != "all"}

        def filter_url(**overrides):
            return "/procurement-plans/%s?%s" % (
                dept.code,
                urlencode(query(**overrides)),
            )

        plan_count = Plan.search_count(filter_domain)
        pager = portal_pager(
            url="/procurement-plans/%s" % dept.code,
            url_args=query(),
            total=plan_count,
            page=page,
            step=PLANS_PER_PAGE,
        )
        plans = Plan.search(
            filter_domain, order="name", limit=PLANS_PER_PAGE, offset=pager["offset"]
        )

        values = self._common_values(fiscal_years, current_fy)
        values.update(
            {
                "dept": dept,
                "filter_url": filter_url,
                "source": source,
                "state": state,
                "search": search,
                "plans": plans,
                "plan_count": plan_count,
                "pager": pager,
                "gov_ids": gov_ids,
                "state_counts": state_counts,
                "all_plan_count": len(all_plans),
                "all_state_counts": Counter(all_plans.mapped("state")),
                "all_total": total,
                "all_gov_total": gov_total,
                "all_rev_total": total - gov_total,
                "all_actual": actual,
                "methods": methods,
            }
        )
        return request.render(
            "procurement_plan_portal.portal_procurement_plan_department", values
        )

    @http.route(
        "/procurement-plans/<string:department_code>/<int:plan_id>",
        type="http",
        auth="public",
        website=True,
    )
    def plan_detail(self, department_code, plan_id, **kw):
        dept = self._get_root_department(department_code)
        if not dept:
            return request.redirect("/procurement-plans")

        plan = (
            request.env["procurement.plan"]
            .sudo()
            .search(self._plan_domain(False, dept) + [("id", "=", plan_id)], limit=1)
        )
        if not plan:
            return request.redirect("/procurement-plans/%s" % dept.code)

        fiscal_years, current_fy = self._get_fiscal_years(
            plan.account_fiscal_year_id.id
        )
        gov_ids = self._get_gov_source_ids()
        months = self._fiscal_months(plan.account_fiscal_year_id)
        month_index = {m[0]: i for i, m in enumerate(months)}
        # Timeline lanes: a marker on the planned month, and a connector bar
        # from the previous planned milestone (positions in % of 12 months)
        milestones, prev = [], None
        for label, field in [
            ("ขอซื้อขอจ้าง (พ.1)", "purchase_request_eta"),
            ("ประกาศจัดซื้อจัดจ้าง", "procurement_announcement_eta"),
            ("อนุมัติ / ลงนาม", "approval_signing_eta"),
            ("ลงนามสัญญา / ใบสั่งซื้อ", "contract_order_signing_eta"),
            ("ตรวจรับ", "acceptance_eta"),
        ]:
            idx = month_index.get(plan[field])
            bar = None
            if idx is not None and prev is not None and idx > prev:
                bar = ((prev + 0.5) / 12 * 100, (idx - prev) / 12 * 100)
            milestones.append(
                {
                    "label": label,
                    "idx": idx,
                    "month": months[idx][1] if idx is not None else "-",
                    "bar": bar,
                }
            )
            if idx is not None:
                prev = idx

        actual = -plan.analytic_account_balance
        values = self._common_values(fiscal_years, current_fy)
        values.update(
            {
                "dept": dept,
                "plan": plan,
                "is_gov": plan.source_analytic_id.id in gov_ids,
                "months": months,
                "milestones": milestones,
                "payment_month_labels": {m[0]: m[2] for m in months},
                "actual": actual,
                "used_pct": round(actual / plan.total_price * 100)
                if plan.total_price
                else 0,
                "state_index": [s for s, _label in PUBLIC_STATES].index(plan.state),
            }
        )
        return request.render(
            "procurement_plan_portal.portal_procurement_plan_detail", values
        )
