from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DisbursementRequest(models.Model):
    """A disbursement request charged to a procurement-plan (investment) budget
    account behaves like a budget-account expense: the line product is the budget
    account's own product (hidden from the user), and the procurement-plan
    dimension is mandatory."""

    _inherit = "disbursement.request"

    is_procurement_plan_expense = fields.Boolean(
        compute="_compute_is_procurement_plan_expense",
        help="รหัสงบประมาณที่เลือกเป็นประเภทงบลงทุน (ทำแผนจัดซื้อจัดจ้าง)",
    )
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แผนจัดซื้อจัดจ้าง (มิติ)",
        compute="_compute_procurement_plan_analytic_id",
        inverse="_inverse_procurement_plan_analytic",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        store=False,
    )

    @api.depends("budget_account_id", "budget_account_id.procurement_plan")
    def _compute_is_procurement_plan_expense(self):
        for rec in self:
            rec.is_procurement_plan_expense = bool(
                rec.budget_account_id.procurement_plan
            )

    @api.depends("analytic_distribution")
    def _compute_procurement_plan_analytic_id(self):
        for rec in self:
            rec.procurement_plan_analytic_id = False
            for key in (rec.analytic_distribution or {}):
                account = self.env["account.analytic.account"].browse(int(key))
                if account.root_plan_id.code == "procurement_plan":
                    rec.procurement_plan_analytic_id = account.id
                    break

    def _inverse_procurement_plan_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("procurement_plan")

    # -- Req 1: line product driven by the budget account -----------------
    @api.onchange("budget_account_id", "line_ids")
    def _onchange_fill_procurement_plan_product(self):
        # Typing shouldn't raise; just keep the (hidden) line product in sync.
        self._fill_procurement_plan_product()

    def _fill_procurement_plan_product(self):
        """Stamp every line with the budget account's product (the product is
        hidden for procurement-plan expenses, so it is not user-editable)."""
        for rec in self.filtered("is_procurement_plan_expense"):
            product = rec.budget_account_id.product_id
            if not product:
                continue
            lines = rec.line_ids.filtered(lambda l: l.product_id != product)
            if lines:
                lines.product_id = product.id

    def _apply_procurement_plan_product(self):
        """Server-side enforcement: resolve the product from the budget account,
        refusing a procurement-plan code with no product configured."""
        for rec in self.filtered("is_procurement_plan_expense"):
            if not rec.budget_account_id.product_id:
                raise UserError(
                    _(
                        "รหัสงบประมาณ %s ยังไม่ได้ผูกสินค้า (product) "
                        "จึงไม่สามารถใช้เป็นค่าใช้จ่ายแผนจัดซื้อจัดจ้างได้"
                    )
                    % (rec.budget_account_id.display_name)
                )
        self._fill_procurement_plan_product()

    def action_submit(self):
        # Enforce server-side (picker/ORM writes bypass the onchange).
        self._apply_procurement_plan_product()
        return super().action_submit()

    # -- Req 3: procurement-plan dimension is mandatory -------------------
    @api.constrains("analytic_distribution", "budget_account_id", "state")
    def _check_procurement_plan_dimension(self):
        for rec in self:
            if rec.state in ("draft", "cancel"):
                continue
            if not rec.is_procurement_plan_expense:
                continue
            if not rec.procurement_plan_analytic_id:
                raise ValidationError(
                    _(
                        "ค่าใช้จ่ายแผนจัดซื้อจัดจ้างต้องระบุมิติแผนจัดซื้อจัดจ้าง"
                        "ให้ครบถ้วน (รหัสงบประมาณ %s)"
                    )
                    % (rec.budget_account_id.display_name)
                )
