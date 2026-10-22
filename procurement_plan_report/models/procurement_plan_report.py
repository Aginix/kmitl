# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Plans that count as "official" for an external submission (draft/cancel out).
REPORTABLE_STATES = ("verified", "in_progress", "done")

# Thai month abbreviations keyed by the MONTH_SELECTION value ("1".."12") the
# plan stores on its ETA fields and installment months.
THAI_MONTH_ABBR = {
    "1": "ม.ค.",
    "2": "ก.พ.",
    "3": "มี.ค.",
    "4": "เม.ย.",
    "5": "พ.ค.",
    "6": "มิ.ย.",
    "7": "ก.ค.",
    "8": "ส.ค.",
    "9": "ก.ย.",
    "10": "ต.ค.",
    "11": "พ.ย.",
    "12": "ธ.ค.",
}

# Thai fiscal year runs Oct(prev)–Sep: Oct/Nov/Dec belong to FY-1.
_PREV_YEAR_MONTHS = {"10", "11", "12"}

# Per-form-type presentation constants. ``is_asset`` selects the budget-account
# side; ``is_multi`` (equipment only) is decided per plan by installment count.
REPORT_TYPES = {
    "construction": {
        "is_asset": False,
        "is_equipment": False,
        "is_multi": False,
        "title": "ที่ดินและสิ่งก่อสร้างที่มีราคาต่อหน่วยสูงกว่า 2 ล้านบาท",
        "expense": "ค่าที่ดินและสิ่งก่อสร้าง/ค่าออกแบบ/ค่าควบคุมงาน (เลือกอย่างใดอย่างหนึ่ง)",
    },
    "equipment": {
        "is_asset": True,
        "is_equipment": True,
        "is_multi": False,
        "title": "ครุภัณฑ์ที่มีราคาต่อหน่วยสูงกว่า 1 แสนบาท",
        "expense": "ค่าครุภัณฑ์",
    },
    "equipment_multi": {
        "is_asset": True,
        "is_equipment": True,
        "is_multi": True,
        "title": "ครุภัณฑ์ที่มีราคาต่อหน่วยสูงกว่า 1 แสนบาท",
        "expense": "ค่าครุภัณฑ์ (กรณี เบิกจ่ายหลายงวดงาน)",
    },
}


class ProcurementPlanReport(models.AbstractModel):
    """แผนการดำเนินการจัดซื้อ/จัดจ้าง submission form (plan vs actual).

    One shared builder (:meth:`get_report_data`) feeds both the OWL client
    action (over RPC) and the XLSX export, so screen and spreadsheet always
    agree. Delivered as three form types (construction / equipment single /
    equipment multi-installment); the type is derived, never stored — see
    ``docs/adr/0002``.
    """

    _name = "procurement.plan.report"
    _description = "Procurement Plan Report"

    # ------------------------------------------------------------------
    # Domain + type derivation
    # ------------------------------------------------------------------
    @api.model
    def _plan_domain(self, options):
        report_type = options.get("report_type") or "construction"
        spec = REPORT_TYPES.get(report_type, REPORT_TYPES["construction"])
        domain = [
            ("company_id", "=", options["company_id"]),
            ("state", "in", list(REPORTABLE_STATES)),
            ("budget_account_id.is_asset", "=", spec["is_asset"]),
        ]
        if options.get("fiscal_year_id"):
            domain.append(("account_fiscal_year_id", "=", options["fiscal_year_id"]))
        dept_ids = options.get("department_ids") or []
        if dept_ids:
            domain.append(("department_analytic_id", "child_of", dept_ids))
        return domain

    @api.model
    def _match_installment_split(self, plan, spec):
        """Equipment splits single vs multi by installment count; construction
        ignores the split."""
        if not spec["is_equipment"]:
            return True
        is_multi = len(plan.payment_ids) > 1
        return is_multi == spec["is_multi"]

    # ------------------------------------------------------------------
    # Label helpers
    # ------------------------------------------------------------------
    @api.model
    def _fy_be(self, fiscal_year):
        """Buddhist-era year as int, parsed from the fiscal year name."""
        try:
            return int("".join(ch for ch in (fiscal_year.name or "") if ch.isdigit()))
        except (TypeError, ValueError):
            return 0

    @api.model
    def _month_label(self, month, fy_be):
        """"ส.ค. 68" — Thai month abbrev + 2-digit พ.ศ. derived from the fiscal
        year (Oct–Dec fall in FY-1). Blank when the month is unset."""
        if not month:
            return ""
        abbr = THAI_MONTH_ABBR.get(str(month), "")
        if not fy_be:
            return abbr
        year = fy_be - 1 if str(month) in _PREV_YEAR_MONTHS else fy_be
        return "%s %02d" % (abbr, year % 100)

    @api.model
    def _program_name(self, activity):
        """แผนงาน = the top-most ancestor of the plan's activity leaf."""
        node = activity
        while node and node.parent_id:
            node = node.parent_id
        return node.name if node else ""

    # ------------------------------------------------------------------
    # Actual (ผล) side — derived from the execution chain, blank until it
    # progresses (ADR-0001). Overridden by the disbursement layer to fill the
    # per-installment actuals. Kept as a hook so this module ships without a
    # hard dependency on that in-flight branch.
    # ------------------------------------------------------------------
    @api.model
    def _prepare_plan_actual(self, plan, fy_be):
        return {
            "total_price": None,
            "unit_price": None,
            "eta": {
                "pr": "",
                "announce": "",
                "approve": "",
                "sign": "",
                "accept": "",
            },
            "installments": [],
            "total_days": None,
            "total_amount": None,
            "contract_no": "",
            "disbursement_no": "",
            "reason": plan.variance_reason or "",
        }

    # ------------------------------------------------------------------
    # Per-plan (แผน side)
    # ------------------------------------------------------------------
    @api.model
    def _prepare_plan_item(self, plan, spec, fy_be):
        installments = [
            {
                "number": pay.number,
                "days": pay.number_of_days,
                "month": self._month_label(pay.month, fy_be),
                "amount": pay.amount,
            }
            for pay in plan.payment_ids.sorted(lambda p: (p.number, p.id))
        ]
        unit_price = (plan.total_price / plan.amount) if plan.amount else 0.0
        return {
            "id": plan.id,
            "name": plan.description or "",
            "amount": plan.amount,
            "unit": plan.unit or "",
            "unit_price": unit_price,
            "total_price": plan.total_price,
            "equipment_category": plan.budget_account_id.name or ""
            if spec["is_equipment"]
            else "",
            "procurement_method": plan.procurement_method_id.name or "",
            "eta": {
                "pr": self._month_label(plan.purchase_request_eta, fy_be),
                "announce": self._month_label(
                    plan.procurement_announcement_eta, fy_be
                ),
                "approve": self._month_label(plan.approval_signing_eta, fy_be),
                "sign": self._month_label(plan.contract_order_signing_eta, fy_be),
                "accept": self._month_label(plan.acceptance_eta, fy_be),
            },
            "installments": installments,
            "total_days": sum(i["days"] or 0 for i in installments),
            "total_amount": sum(i["amount"] or 0.0 for i in installments),
            "actual": self._prepare_plan_actual(plan, fy_be),
        }

    # ------------------------------------------------------------------
    # Grouping — ปีงบ + หน่วยงาน are the report scope; within it group by
    # แหล่งเงิน → แผนงาน → (ผลผลิต: deferred) → กิจกรรม.
    # ------------------------------------------------------------------
    @api.model
    def _group_key(self, plan):
        return (
            plan.department_analytic_id.id,
            plan.source_analytic_id.id,
            plan.activity_analytic_id.id,
        )

    @api.model
    def get_report_data(self, options):
        """Build the report. ``options`` keys: ``company_id``,
        ``report_type``, ``fiscal_year_id``, ``department_ids`` (list)."""
        options = options or {}
        report_type = options.get("report_type") or "construction"
        spec = REPORT_TYPES.get(report_type, REPORT_TYPES["construction"])
        company_id = options.get("company_id") or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        options = dict(options, company_id=company_id, report_type=report_type)

        fiscal_year = self.env["account.fiscal.year"].browse(
            options.get("fiscal_year_id")
        )
        fy_be = self._fy_be(fiscal_year) if fiscal_year else 0

        plans = self.env["procurement.plan"].search(
            self._plan_domain(options), order="name"
        )
        plans = plans.filtered(lambda p: self._match_installment_split(p, spec))

        groups = {}
        for plan in plans:
            key = self._group_key(plan)
            group = groups.get(key)
            if group is None:
                activity = plan.activity_analytic_id
                group = groups[key] = {
                    "source_name": plan.source_analytic_id.name or "",
                    "department_name": plan.department_analytic_id.name or "",
                    "program_name": self._program_name(activity),
                    "output_name": "",  # ผลผลิต — deferred (ADR/grill 2026-08-18)
                    "activity_name": activity.name or "",
                    "items": [],
                }
            group["items"].append(self._prepare_plan_item(plan, spec, fy_be))

        ordered = sorted(
            groups.values(),
            key=lambda g: (
                g["department_name"],
                g["source_name"],
                g["program_name"],
                g["activity_name"],
            ),
        )

        return {
            "report_type": report_type,
            "title": spec["title"],
            "expense": spec["expense"],
            "is_equipment": spec["is_equipment"],
            "is_multi": spec["is_multi"],
            "company_name": company.display_name,
            "fiscal_year_name": fiscal_year.name if fiscal_year else "",
            "currency_id": company.currency_id.id,
            "groups": ordered,
        }

    # ------------------------------------------------------------------
    # XLSX export — return the report action so the OWL client action can
    # ``doAction`` it. Filters travel in ``data`` (no persisted state), so the
    # workbook mirrors the screen exactly.
    # ------------------------------------------------------------------
    @api.model
    def action_export_xlsx(self, options):
        options = options or {}
        carrier = self.env["procurement.plan.report.wizard"].create(
            {
                "company_id": options.get("company_id") or self.env.company.id,
                "report_type": options.get("report_type") or "construction",
                "fiscal_year_id": options.get("fiscal_year_id"),
            }
        )
        report = self.env.ref(
            "procurement_plan_report.action_procurement_plan_report_xlsx"
        )
        return report.report_action(carrier, data={"options": options})
