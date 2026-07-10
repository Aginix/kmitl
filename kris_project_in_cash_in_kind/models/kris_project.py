from odoo import api, fields, models
from odoo.tools import float_compare


class KrisProject(models.Model):
    _inherit = "kris.project"

    is_research_category = fields.Boolean(
        compute="_compute_is_research_category",
    )
    in_cash = fields.Monetary(
        string="In Cash",
        tracking=True,
        help="เงินสดที่โครงการรับจริงจากผู้ว่าจ้าง (ใช้เฉพาะงานวิจัย)",
    )
    in_kind = fields.Monetary(
        string="In Kind",
        tracking=True,
        help="ทุนสิ่งของ/แรงงานสมทบที่ไม่ผ่านกระแสเงินสด (ใช้เฉพาะงานวิจัย)",
    )
    # Redefine project_value as a stored compute so research projects derive
    # it from in_cash + in_kind. readonly=False keeps the field editable for
    # non-research projects, where the compute is a no-op and Odoo falls back
    # to the user-input value.
    project_value = fields.Monetary(
        compute="_compute_project_value",
        store=True,
        readonly=False,
    )
    # cash_target anchors every cash-flow computation. On research projects
    # only in_cash is money that actually reaches KRIS; in_kind is matching
    # funds recorded for reporting and must not drive maintenance fees or
    # revenue-remaining comparisons.
    cash_target = fields.Monetary(
        compute="_compute_cash_target",
        store=True,
    )

    @api.depends("project_category_id")
    def _compute_is_research_category(self):
        research = self.env.ref(
            "kris_project.project_category_research", raise_if_not_found=False
        )
        for rec in self:
            rec.is_research_category = bool(research) and (
                rec.project_category_id == research
            )

    @api.depends("in_cash", "in_kind", "is_research_category")
    def _compute_project_value(self):
        # Research: project_value is derived from the in_cash + in_kind split.
        # Non-research: leave rec.project_value untouched so the field keeps
        # its user-input semantics (readonly=False on the compute).
        for rec in self:
            if rec.is_research_category:
                rec.project_value = rec.in_cash + rec.in_kind

    @api.depends("project_value", "in_cash", "is_research_category")
    def _compute_cash_target(self):
        for rec in self:
            rec.cash_target = rec.in_cash if rec.is_research_category else rec.project_value

    # -- Overrides on the base cash-flow computes ------------------------
    # Each override keeps the parent's semantics but swaps project_value for
    # cash_target so in_kind money never leaks into maintenance fees or
    # revenue-remaining/installment-mismatch comparisons.

    @api.depends("cash_target", "equipment_cost")
    def _compute_operating_expense(self):
        super()._compute_operating_expense()
        for rec in self:
            if rec.is_research_category:
                rec.operating_expense = rec.cash_target - rec.equipment_cost

    @api.depends(
        "installment_ids.received_from_employer",
        "receipt_ids.amount",
        "receipt_ids.net_amount",
        "receipt_ids.extra_income",
        "cash_target",
    )
    def _compute_totals(self):
        super()._compute_totals()
        for rec in self:
            if rec.is_research_category:
                diff = rec.cash_target - rec.total_received_amount
                rec.revenue_remaining = max(0.0, diff)
                rec.over_revenue = max(0.0, -diff)

    @api.depends(
        "maintenance_deduction_amount",
        "operating_expense",
        "allocation_line_ids.estimated_amount",
        "installment_ids.maintenance_fee",
        "installment_ids.extra_income",
        "total_installment_amount",
        "cash_target",
        "extra_value",
        "no_installment_tracking",
        "state",
        "receipt_ids",
    )
    def _compute_warnings(self):
        super()._compute_warnings()
        prec = self.env["decimal.precision"].precision_get("Account")
        for rec in self:
            if (
                rec.is_research_category
                and rec.installment_ids
                and not rec.no_installment_tracking
            ):
                rec.warn_installment_total_mismatch = (
                    float_compare(
                        rec.total_installment_amount,
                        rec.cash_target,
                        precision_digits=prec,
                    )
                    != 0
                )

    @api.onchange("project_category_id")
    def _onchange_project_category_id_research_switch(self):
        # When a user switches a draft project into the research category and
        # in_cash / in_kind are still empty, seed in_cash from the existing
        # project_value so the derivation does not wipe the value they already
        # entered. Mirrors the post_init_hook backfill for existing records.
        if (
            self.is_research_category
            and not self.in_cash
            and not self.in_kind
            and self.project_value
        ):
            self.in_cash = self.project_value
            self.in_kind = 0.0
