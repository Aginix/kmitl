from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetMoveLine(models.Model):
    """Narrow the transfer-line procurement-plan picker to the plans whose budget
    code, fiscal year and dimensions match what the line already carries.

    Progressive: a dimension still blank on the line does not filter. The
    blocking exception rule (``budget_transfer_exception_procurement_plan``)
    stays the final gate at ยืนยัน. Plans are searched as superuser; the analytic
    OU filter still governs what the picker shows.
    """

    _inherit = "budget.move.line"

    allowed_procurement_plan_analytic_ids = fields.Many2many(
        "account.analytic.account",
        compute="_compute_allowed_procurement_plan_analytic_ids",
    )

    @api.depends(
        "account_id",
        "activity_analytic_id",
        "fund_analytic_id",
        "department_analytic_id",
        "source_analytic_id",
        "move_id.account_fiscal_year_id",
    )
    @api.depends_context("transfer_fiscal_year_id")
    def _compute_allowed_procurement_plan_analytic_ids(self):
        Plan = self.env["procurement.plan"].sudo()
        for line in self:
            domain = [("analytic_account_id", "!=", False)]
            if line.account_id:
                domain.append(("budget_account_id", "=", line.account_id.id))
            fiscal_year = line._transfer_fiscal_year()
            if fiscal_year:
                domain.append(("account_fiscal_year_id", "=", fiscal_year.id))
            for dim in (
                "department_analytic_id",
                "activity_analytic_id",
                "source_analytic_id",
            ):
                if line[dim]:
                    domain.append((dim, "=", line[dim].id))
            plans = Plan.search(domain)
            # Non-stored on procurement.plan — filter in Python.
            if line.fund_analytic_id:
                plans = plans.filtered(
                    lambda p: p.fund_analytic_id == line.fund_analytic_id
                )
            line.allowed_procurement_plan_analytic_ids = plans.analytic_account_id

    def action_open_procurement_plan(self):
        """Open the line's procurement.plan in a new browser tab.

        Looked up as superuser so the button works on every row; the opened
        form applies the normal access rules.
        """
        self.ensure_one()
        record = (
            self.env["procurement.plan"]
            .sudo()
            .search(
                [("analytic_account_id", "=", self.procurement_plan_analytic_id.id)],
                limit=1,
            )
        )
        if not record:
            raise UserError(
                _("ไม่พบรายการที่ผูกกับมิติ %s")
                % self.procurement_plan_analytic_id.display_name
            )
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": f"/web#id={record.id}&model=procurement.plan&view_type=form",
        }

    def _get_pool_owner_commitment(self):
        """The reservations of the plan a ``procurement_plan`` tag names, so a
        transfer onto/off its coordinate tops it up / releases it (budget
        ADR-0017, Q5)."""
        commitments = super()._get_pool_owner_commitment()
        if self.procurement_plan_analytic_id:
            plans = (
                self.env["procurement.plan"]
                .sudo()
                .search(
                    [("analytic_account_id", "=", self.procurement_plan_analytic_id.id)]
                )
            )
            commitments |= plans.budget_commitment_ids
        return commitments
