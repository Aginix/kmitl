# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models

from .procurement_plan_report import REPORTABLE_STATES


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    # The one actual-side value the execution chain cannot supply: why ผล
    # diverged from แผน (the หมายเหตุ / เหตุผล column). ADR-0001.
    variance_reason = fields.Char(
        string="เหตุผล (ผลต่างจากแผน)",
        help="ระบุเหตุผลเมื่อผลการดำเนินการต่างจากแผน แสดงในคอลัมน์หมายเหตุของรายงาน",
    )

    # The smart button is meaningful once the plan is official (reportable
    # state) and carries a budget account to classify it into a form type.
    show_report_button = fields.Boolean(compute="_compute_show_report_button")

    @api.depends("state", "budget_account_id")
    def _compute_show_report_button(self):
        for plan in self:
            plan.show_report_button = (
                plan.state in REPORTABLE_STATES and bool(plan.budget_account_id)
            )

    def _report_type(self):
        """Derive which of the three form types this plan prints under
        (mirrors ``procurement.plan.report._plan_domain`` / ADR-0002)."""
        self.ensure_one()
        if not self.budget_account_id.is_asset:
            return "construction"
        return "equipment_multi" if len(self.payment_ids) > 1 else "equipment"

    def action_open_procurement_report(self):
        """Smart button: open the report screen for this plan's own form type,
        pre-scoped to its ปีงบ + หน่วยงาน."""
        self.ensure_one()
        report_type = self._report_type()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "procurement_plan_report.action_procurement_plan_report_%s" % report_type
        )
        action["context"] = dict(
            self.env.context,
            report_type=report_type,
            default_fiscal_year_id=self.account_fiscal_year_id.id,
            default_department_id=self.department_analytic_id.id,
        )
        action["name"] = _("รายงานแผนจัดซื้อจัดจ้าง")
        return action
