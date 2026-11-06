from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AdvancePaymentProjectLine(models.Model):
    """One expense item of the project a loan borrows against."""

    _name = "advance.payment.project.line"
    _description = "Advance Payment Project Expense Item"
    _order = "id"

    advance_payment_id = fields.Many2one(
        "advance.payment", required=True, ondelete="cascade", index=True
    )
    project_line_id = fields.Many2one(
        "project.budget.line", required=True, ondelete="restrict", index=True
    )
    # sudo: the borrower usually cannot read the project's lines.
    name = fields.Char(
        related="project_line_id.name", string="รายการ", compute_sudo=True
    )
    category_id = fields.Many2one(
        related="project_line_id.category_id", string="หมวด", compute_sudo=True
    )
    line_amount = fields.Float(
        related="project_line_id.amount", string="วงเงินรายการ", compute_sudo=True
    )
    remaining_amount = fields.Float(
        related="project_line_id.remaining_amount",
        string="คงเหลือ",
        compute_sudo=True,
    )
    currency_id = fields.Many2one(related="advance_payment_id.currency_id")
    amount = fields.Monetary(string="ยอดยืม", currency_field="currency_id")
    exceeds_remaining = fields.Boolean(compute="_compute_exceeds_remaining")

    @api.depends("amount", "remaining_amount", "advance_payment_id.state")
    def _compute_exceeds_remaining(self):
        for rec in self:
            # Once submitted the loan counts itself in `remaining_amount`.
            counted = rec.advance_payment_id.state not in ("draft", "cancel")
            own = rec.amount if counted else 0.0
            rec.exceeds_remaining = (
                float_compare(
                    rec.amount,
                    rec.remaining_amount + own,
                    precision_rounding=rec.currency_id.rounding,
                )
                > 0
            )

    @api.constrains("amount", "project_line_id", "advance_payment_id")
    def _check_line(self):
        for rec in self:
            line = rec.project_line_id.sudo()
            if rec.amount < 0:
                raise ValidationError(_("ยอดยืมต้องไม่ติดลบ"))
            if line.project_id != rec.advance_payment_id.kmitl_project_id.sudo():
                raise ValidationError(
                    _("รายการ %s ไม่ใช่ของโครงการที่อ้างอิง", line.name)
                )
            if line.budget_type != "expense" or line.is_loan_via_pr_only:
                raise ValidationError(
                    _("รายการ %s ต้องยืมผ่านใบ PR เท่านั้น", line.name)
                )

    def _check_editable(self, advances):
        for advance in advances:
            if advance.state != "draft":
                raise ValidationError(
                    _("แก้ไขรายการยืมได้เฉพาะสัญญาที่ยังเป็นฉบับร่าง")
                )
            advance.check_access_rule("write")

    @api.model_create_multi
    def create(self, vals_list):
        advances = self.env["advance.payment"].browse(
            [v["advance_payment_id"] for v in vals_list]
        )
        self._check_editable(advances)
        return super().create(vals_list)

    def write(self, vals):
        self._check_editable(self.advance_payment_id)
        return super().write(vals)

    def unlink(self):
        self._check_editable(self.advance_payment_id)
        return super().unlink()
