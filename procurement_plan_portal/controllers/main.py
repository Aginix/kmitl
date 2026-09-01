import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ProcurementPlanPortal(http.Controller):

    @http.route("/procurement-plans", type="http", auth="public", website=True)
    def overview(self, fiscal_year_id=None, **kw):
        env = request.env

        # Get fiscal years for filter dropdown
        fiscal_years = env["account.fiscal.year"].sudo().search(
            [], order="date_from desc"
        )

        # Default to latest fiscal year
        if fiscal_year_id:
            fiscal_year_id = int(fiscal_year_id)
            current_fy = env["account.fiscal.year"].sudo().browse(fiscal_year_id)
            if not current_fy.exists():
                current_fy = fiscal_years[:1]
        else:
            current_fy = fiscal_years[:1]

        # Get root departments
        departments_plan = env.ref(
            "account_analytic_kmitl.analytic_plan_departments"
        )
        root_departments = env["account.analytic.account"].sudo().search(
            [
                ("plan_id", "=", departments_plan.id),
                ("parent_id", "=", False),
            ],
            order="code",
        )

        # Fetch the two fixed source accounts by code
        sources_plan = env.ref("account_analytic_kmitl.analytic_plan_sources")
        src_gov = env["account.analytic.account"].sudo().search(
            [("plan_id", "=", sources_plan.id), ("code", "=", "1")], limit=1
        )
        src_rev = env["account.analytic.account"].sudo().search(
            [("plan_id", "=", sources_plan.id), ("code", "=", "2")], limit=1
        )

        dept_rows = []
        grand_total_count = 0
        grand_total_price = 0.0
        grand_gov_count = grand_gov_total = 0
        grand_rev_count = grand_rev_total = 0.0

        for dept in root_departments:
            # Get all descendants via parent_path
            child_dept_ids = env["account.analytic.account"].sudo().search(
                [("parent_path", "like", dept.parent_path + "%")]
            ).ids

            domain = [
                ("state", "!=", "draft"),
                ("department_analytic_id", "in", child_dept_ids),
            ]
            if current_fy:
                domain.append(("account_fiscal_year_id", "=", current_fy.id))

            plans = env["procurement.plan"].sudo().search(domain)
            plan_count = len(plans)
            if plan_count == 0:
                continue

            total_price = sum(plans.mapped("total_price"))
            grand_total_count += plan_count
            grand_total_price += total_price

            gov_plans = plans.filtered(lambda p: p.source_analytic_id == src_gov)
            rev_plans = plans.filtered(lambda p: p.source_analytic_id == src_rev)
            gov_count = len(gov_plans)
            gov_total = sum(gov_plans.mapped("total_price"))
            rev_count = len(rev_plans)
            rev_total = sum(rev_plans.mapped("total_price"))
            grand_gov_count += gov_count
            grand_gov_total += gov_total
            grand_rev_count += rev_count
            grand_rev_total += rev_total

            dept_rows.append({
                "dept": dept,
                "plan_count": plan_count,
                "total_price": total_price,
                "gov_count": gov_count,
                "gov_total": gov_total,
                "rev_count": rev_count,
                "rev_total": rev_total,
            })

        values = {
            "fiscal_years": fiscal_years,
            "current_fy": current_fy,
            "dept_rows": dept_rows,
            "grand_total_count": grand_total_count,
            "grand_total_price": grand_total_price,
            "grand_gov_count": grand_gov_count,
            "grand_gov_total": grand_gov_total,
            "grand_rev_count": grand_rev_count,
            "grand_rev_total": grand_rev_total,
        }
        return request.render(
            "procurement_plan_portal.portal_procurement_plans", values
        )

    @http.route(
        "/procurement-plans/<string:department_code>",
        type="http",
        auth="public",
        website=True,
    )
    def department_detail(self, department_code, fiscal_year_id=None, source=None, **kw):
        env = request.env

        departments_plan = env.ref(
            "account_analytic_kmitl.analytic_plan_departments"
        )
        dept = env["account.analytic.account"].sudo().search(
            [
                ("plan_id", "=", departments_plan.id),
                ("parent_id", "=", False),
                ("code", "=", department_code),
            ],
            limit=1,
        )
        if not dept:
            return request.redirect("/procurement-plans")

        # Get fiscal years
        fiscal_years = env["account.fiscal.year"].sudo().search(
            [], order="date_from desc"
        )
        if fiscal_year_id:
            fiscal_year_id = int(fiscal_year_id)
            current_fy = env["account.fiscal.year"].sudo().browse(fiscal_year_id)
            if not current_fy.exists():
                current_fy = fiscal_years[:1]
        else:
            current_fy = fiscal_years[:1]

        # Fetch the two fixed source accounts by code
        sources_plan = env.ref("account_analytic_kmitl.analytic_plan_sources")
        src_gov = env["account.analytic.account"].sudo().search(
            [("plan_id", "=", sources_plan.id), ("code", "=", "1")], limit=1
        )
        src_rev = env["account.analytic.account"].sudo().search(
            [("plan_id", "=", sources_plan.id), ("code", "=", "2")], limit=1
        )

        # Get all child departments via parent_path
        child_dept_ids = env["account.analytic.account"].sudo().search(
            [("parent_path", "like", dept.parent_path + "%")]
        ).ids

        domain = [
            ("state", "!=", "draft"),
            ("department_analytic_id", "in", child_dept_ids),
        ]
        if current_fy:
            domain.append(("account_fiscal_year_id", "=", current_fy.id))

        all_plans = env["procurement.plan"].sudo().search(domain, order="name")

        gov_plans = all_plans.filtered(lambda p: p.source_analytic_id == src_gov)
        rev_plans = all_plans.filtered(lambda p: p.source_analytic_id == src_rev)
        gov_total = sum(gov_plans.mapped("total_price"))
        rev_total = sum(rev_plans.mapped("total_price"))

        # Apply source filter for displayed plans
        if source == "gov":
            plans = gov_plans
        elif source == "rev":
            plans = rev_plans
        else:
            source = "all"
            plans = all_plans

        total_price = sum(plans.mapped("total_price"))
        total_actual = sum(-p.analytic_account_balance for p in plans)

        # Summary stats always from all_plans (unfiltered)
        all_total_price = sum(all_plans.mapped("total_price"))
        all_method_breakdown = {}
        for plan in all_plans:
            method_name = (
                plan.procurement_method_id.name
                if plan.procurement_method_id
                else "ไม่ระบุ"
            )
            if method_name not in all_method_breakdown:
                all_method_breakdown[method_name] = {"count": 0, "total": 0.0}
            all_method_breakdown[method_name]["count"] += 1
            all_method_breakdown[method_name]["total"] += plan.total_price

        values = {
            "dept": dept,
            "fiscal_years": fiscal_years,
            "current_fy": current_fy,
            "source": source,
            "plans": plans,
            "plan_count": len(plans),
            "total_price": total_price,
            "gov_total": gov_total,
            "rev_total": rev_total,
            "total_actual": total_actual,
            "src_gov": src_gov,
            "src_rev": src_rev,
            # Summary stats (always unfiltered)
            "all_plan_count": len(all_plans),
            "all_total_price": all_total_price,
            "all_method_breakdown": all_method_breakdown,
        }
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
        env = request.env

        departments_plan = env.ref(
            "account_analytic_kmitl.analytic_plan_departments"
        )
        dept = env["account.analytic.account"].sudo().search(
            [
                ("plan_id", "=", departments_plan.id),
                ("parent_id", "=", False),
                ("code", "=", department_code),
            ],
            limit=1,
        )
        if not dept:
            return request.redirect("/procurement-plans")

        plan = env["procurement.plan"].sudo().browse(plan_id)
        if not plan.exists() or plan.state == "draft":
            return request.redirect(f"/procurement-plans/{department_code}")

        sources_plan = env.ref("account_analytic_kmitl.analytic_plan_sources")
        src_gov = env["account.analytic.account"].sudo().search(
            [("plan_id", "=", sources_plan.id), ("code", "=", "1")], limit=1
        )
        src_rev = env["account.analytic.account"].sudo().search(
            [("plan_id", "=", sources_plan.id), ("code", "=", "2")], limit=1
        )

        # State label map
        state_labels = {
            "to_verify": "รอตรวจสอบข้อมูล",
            "verified": "รอดำเนินการ",
            "in_progress": "กำลังดำเนินการ",
            "done": "เสร็จสิ้น",
            "cancel": "ยกเลิก",
        }
        month_labels = {
            "1": "มกราคม", "2": "กุมภาพันธ์", "3": "มีนาคม",
            "4": "เมษายน", "5": "พฤษภาคม", "6": "มิถุนายน",
            "7": "กรกฎาคม", "8": "สิงหาคม", "9": "กันยายน",
            "10": "ตุลาคม", "11": "พฤศจิกายน", "12": "ธันวาคม",
        }

        values = {
            "dept": dept,
            "plan": plan,
            "src_gov": src_gov,
            "src_rev": src_rev,
            "state_labels": state_labels,
            "month_labels": month_labels,
            "actual": -plan.analytic_account_balance,
        }
        return request.render(
            "procurement_plan_portal.portal_procurement_plan_detail", values
        )
