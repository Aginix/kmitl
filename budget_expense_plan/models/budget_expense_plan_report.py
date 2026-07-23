# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Actual (ผล) engine + grid data + xlsx for the expense plan.

The grid is derived live from the unit's chosen activities and the Template's
two compositions (Activity->Funds, Fund->Budget Lines) -- ADR-0004. The Actual
column reads เบิกจ่ายจริง from the budget ledger ``budget.move.line``
(``move_type='consume'``), resolved by each Budget Line's ``expr`` over ``code``
and scoped by month + dimensions (ADR-0003). Dimension scoping uses
``analytic_distribution`` (source of truth) because the typed convenience
columns are not reliably populated on consume lines (ADR-0003 caveat).
"""
from odoo import _, api, models
from odoo.exceptions import UserError

from .formula import CodeResolver, eval_formula

THAI_MONTH_ABBR = {
    1: "ม.ค.", 2: "ก.พ.", 3: "มี.ค.", 4: "เม.ย.", 5: "พ.ค.", 6: "มิ.ย.",
    7: "ก.ค.", 8: "ส.ค.", 9: "ก.ย.", 10: "ต.ค.", 11: "พ.ย.", 12: "ธ.ค.",
}


class BudgetExpensePlan(models.Model):
    _inherit = "budget.expense.plan"

    # ------------------------------------------------------------------ #
    # Month axis (Thai fiscal year: derived from the FY start month)
    # ------------------------------------------------------------------ #
    def _fy_month_order(self):
        self.ensure_one()
        start = self.fiscal_year_id.date_from
        start_month = start.month if start else 10
        return [((start_month - 1 + i) % 12) + 1 for i in range(12)]

    # ------------------------------------------------------------------ #
    # Actual aggregation  (budget.move.line consume)
    # ------------------------------------------------------------------ #
    def _child_ids(self, analytic):
        return (
            self.env["account.analytic.account"]
            .search([("id", "child_of", analytic.id)])
            .ids
        )

    def _aggregate_actual(self, pairs):
        """Return ``cache[(activity_id, fund_id)][month] = {code: consume}``.
        One ``read_group`` on ``budget.move.line`` per distinct (activity, fund)
        pair, scoped to this document's ส่วนงาน + แหล่งเงิน + ปีงบ and posted
        consume. Consume is credit-negative, so it is negated to positive."""
        self.ensure_one()
        MoveLine = self.env["budget.move.line"]
        base = [
            ("parent_state", "=", "posted"),
            ("move_type", "=", "consume"),
            ("account_fiscal_year_id", "=", self.fiscal_year_id.id),
            ("source_analytic_id", "=", self.source_analytic_id.id),
            ("analytic_distribution", "in", self._child_ids(self.department_analytic_id)),
        ]
        cache = {}
        for activity, fund in pairs:
            domain = base + [
                ("analytic_distribution", "in", self._child_ids(activity)),
                ("analytic_distribution", "in", self._child_ids(fund)),
            ]
            by_month = {}
            for grp in MoveLine.read_group(
                domain, ["balance:sum"], ["code", "date:month"], lazy=False
            ):
                rng = (grp.get("__range") or {}).get("date:month") or {}
                start = rng.get("from")
                code = grp.get("code")
                if not (start and code):
                    continue
                month = int(start[5:7])
                slot = by_month.setdefault(month, {})
                slot[code] = slot.get(code, 0.0) - (grp.get("balance") or 0.0)
            cache[(activity.id, fund.id)] = by_month
        return cache

    # ------------------------------------------------------------------ #
    # Grid data for the OWL client action
    # ------------------------------------------------------------------ #
    @api.model
    def get_grid_data(self, plan_id):
        plan = self.browse(plan_id)
        plan.ensure_one()
        chosen = plan.template_activity_ids.sorted(lambda a: (a.sequence, a.id))
        months_order = plan._fy_month_order()
        months = [
            {"m": m, "label": THAI_MONTH_ABBR.get(m, str(m)), "quarter": (i // 3) + 1}
            for i, m in enumerate(months_order)
        ]

        planned = {}
        for amt in plan.amount_ids:
            key = (
                amt.activity_analytic_id.id,
                amt.fund_analytic_id.id,
                amt.budget_line_id.id,
                amt.month,
            )
            planned[key] = amt.amount

        # (activity, fund) pairs for actual aggregation
        pairs = set()
        for ta in chosen:
            for tf in ta.fund_ids:
                pairs.add((ta.activity_analytic_id, tf.fund_analytic_id))
        cache = plan._aggregate_actual(pairs)

        rows = []
        for ta in chosen:
            activity = ta.activity_analytic_id
            for tf in ta.fund_ids.sorted(lambda f: (f.sequence, f.id)):
                fund = tf.fund_analytic_id
                by_month = cache.get((activity.id, fund.id), {})
                for bl in tf.budget_line_ids.sorted(
                    lambda b: (b.category_id.code or "", b.sequence, b.id)
                ):
                    plan_by_m, actual_by_m = {}, {}
                    for m in months_order:
                        plan_by_m[m] = planned.get((activity.id, fund.id, bl.id, m), 0.0)
                        resolver = CodeResolver(by_month.get(m, {}))
                        actual_by_m[m] = eval_formula(bl.expr, resolver)
                    rows.append(
                        {
                            "template_activity_id": ta.id,
                            "activity_id": activity.id,
                            "activity_name": activity.display_name,
                            "fund_id": fund.id,
                            "fund_name": fund.display_name,
                            "budget_line_id": bl.id,
                            "budget_line_name": bl.name,
                            "category_name": bl.category_id.name,
                            "plan": plan_by_m,
                            "actual": actual_by_m,
                        }
                    )

        available = [
            {"id": ta.id, "name": ta.activity_analytic_id.display_name}
            for ta in plan.template_id.activity_ids.sorted(lambda a: (a.sequence, a.id))
            if ta not in chosen
        ]
        return {
            "plan_id": plan.id,
            "name": plan.display_name,
            "state": plan.state,
            "editable": plan.state != "active",
            "currency_id": plan.currency_id.id,
            "months": months,
            "rows": rows,
            "available_activities": available,
        }

    @api.model
    def set_amounts(self, plan_id, changes):
        """Upsert / unlink monthly plan cells keyed by the dimension tuple.
        ``changes`` = list of ``{activity_id, fund_id, budget_line_id, month,
        amount}``. Zero removes the cell. Blocked when the plan is locked."""
        plan = self.browse(plan_id)
        plan.ensure_one()
        if plan.state == "active":
            raise UserError(_("แผนอยู่ในสถานะ 'แผนใช้งาน' (ล็อก) แก้ไขยอดไม่ได้"))
        Amount = self.env["budget.expense.plan.amount"]
        for ch in changes:
            key = [
                ("plan_id", "=", plan.id),
                ("activity_analytic_id", "=", int(ch["activity_id"])),
                ("fund_analytic_id", "=", int(ch["fund_id"])),
                ("budget_line_id", "=", int(ch["budget_line_id"])),
                ("month", "=", int(ch["month"])),
            ]
            amount = ch.get("amount") or 0.0
            existing = Amount.search(key, limit=1)
            if amount:
                if existing:
                    existing.amount = amount
                else:
                    Amount.create(
                        {
                            "plan_id": plan.id,
                            "activity_analytic_id": int(ch["activity_id"]),
                            "fund_analytic_id": int(ch["fund_id"]),
                            "budget_line_id": int(ch["budget_line_id"]),
                            "month": int(ch["month"]),
                            "amount": amount,
                        }
                    )
            elif existing:
                existing.unlink()
        return True

    @api.model
    def add_activity(self, plan_id, template_activity_id):
        plan = self.browse(plan_id)
        plan.ensure_one()
        if plan.state == "active":
            raise UserError(_("แผนอยู่ในสถานะ 'แผนใช้งาน' (ล็อก) แก้ไขไม่ได้"))
        plan.write({"template_activity_ids": [(4, int(template_activity_id))]})
        return True

    @api.model
    def remove_activity(self, plan_id, template_activity_id):
        plan = self.browse(plan_id)
        plan.ensure_one()
        if plan.state == "active":
            raise UserError(_("แผนอยู่ในสถานะ 'แผนใช้งาน' (ล็อก) แก้ไขไม่ได้"))
        # Amounts stay (tuple-keyed); they simply stop rendering (soft-hide).
        plan.write({"template_activity_ids": [(3, int(template_activity_id))]})
        return True


class BudgetExpensePlanXlsx(models.AbstractModel):
    """XLSX rendering of one Plan Document as the แผน/ผล table (the sample
    layout): rows = the chosen (Activity/Fund/Budget Line) with แผน & ผล per
    month + a รวม column."""

    _name = "report.budget_expense_plan.expense_plan_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, plans):
        hdr = workbook.add_format(
            {"bold": True, "border": 1, "bg_color": "#DDEBF7", "align": "center"}
        )
        money = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        money_bold = workbook.add_format(
            {"border": 1, "bold": True, "num_format": "#,##0.00"}
        )
        label = workbook.add_format({"border": 1})

        for plan in plans:
            grid = self.env["budget.expense.plan"].get_grid_data(plan.id)
            sheet = workbook.add_worksheet((plan.name or "แผน")[:31])
            months = grid["months"]

            sheet.merge_range(
                0, 0, 0, 2 + len(months) * 2,
                _("แผนการเบิกจ่าย: %s") % grid["name"], hdr,
            )
            row = 2
            sheet.write(row, 0, _("ด้าน/กองทุน/รายการงบ"), hdr)
            col = 1
            for mo in months:
                sheet.merge_range(row, col, row, col + 1, mo["label"], hdr)
                col += 2
            sheet.write(row, col, _("รวม"), hdr)
            row += 1
            sheet.write(row, 0, "", hdr)
            col = 1
            for _mo in months:
                sheet.write(row, col, _("แผน"), hdr)
                sheet.write(row, col + 1, _("ผล"), hdr)
                col += 2
            sheet.write(row, col, "", hdr)
            row += 1

            for r in grid["rows"]:
                name = " / ".join(
                    [r["activity_name"] or "", r["fund_name"] or "",
                     r["budget_line_name"] or ""]
                )
                sheet.write(row, 0, name, label)
                col = 1
                plan_total = 0.0
                for mo in months:
                    pv = r["plan"].get(str(mo["m"]), r["plan"].get(mo["m"], 0.0))
                    av = r["actual"].get(str(mo["m"]), r["actual"].get(mo["m"], 0.0))
                    sheet.write(row, col, pv, money)
                    sheet.write(row, col + 1, av, money)
                    plan_total += pv or 0.0
                    col += 2
                sheet.write(row, col, plan_total, money_bold)
                row += 1
            sheet.set_column(0, 0, 40)
            sheet.set_column(1, 2 + len(months) * 2, 12)
