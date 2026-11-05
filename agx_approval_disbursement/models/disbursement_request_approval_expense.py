from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DisbursementRequestApprovalExpense(models.Model):
    """ค่าใช้จ่ายที่ขอเบิก — the Expense breakdown of a ใบขอเบิก that references
    an approval request (agx_approval ADR-0010). Kept apart from the payee
    lines: the recipient is not always the one who spent (an advance or a
    loan), so which Expenses the ใบขอเบิก covers is stated on its own."""

    _name = "disbursement.request.approval.expense"
    _description = "Disbursement Request Approval Expense"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        "disbursement.request",
        string="ใบขอเบิก",
        required=True,
        ondelete="cascade",
        index=True,
    )
    approval_request_line_id = fields.Many2one(
        "approval.request.line",
        string="ค่าใช้จ่ายของคำขอ",
        required=True,
        ondelete="restrict",
        index=True,
    )
    description = fields.Text(string="ชี้แจงรายละเอียด")
    currency_id = fields.Many2one(related="request_id.currency_id")
    amount = fields.Monetary(
        string="ยอดขอเบิกครั้งนี้",
        currency_field="currency_id",
        required=True,
    )

    approved_amount = fields.Monetary(
        string="จำนวนเงินตามใบขออนุมัติ",
        currency_field="currency_id",
        related="approval_request_line_id.total_amount",
    )
    remaining_after = fields.Monetary(
        string="คงเหลือหลังเบิกครั้งนี้",
        currency_field="currency_id",
        compute="_compute_remaining_after",
        help="จำนวนเงินตามใบขออนุมัติ − ที่ใบขอเบิกอื่นของคำขอเบิกไปแล้วหรือกำลังเบิก "
        "− ยอดขอเบิกครั้งนี้",
    )

    @api.depends(
        "approval_request_line_id",
        "amount",
        "request_id.approval_expense_ids.amount",
        "request_id.approval_expense_ids.approval_request_line_id",
    )
    def _compute_remaining_after(self):
        """What the Expense has left once this ใบขอเบิก is counted — the other
        non-cancelled ใบขอเบิก of the request from the database, this one from
        the form, so it follows the edit before it is saved."""
        for row in self:
            line = row.approval_request_line_id
            if not line:
                row.remaining_after = 0.0
                continue
            dr = row.request_id
            others = line.sudo().disbursement_expense_ids.filtered(
                lambda r: r.request_id != dr._origin
                and r.request_id.state != "cancel"
                and r.request_id.approval_request_id == line.request_id
            )
            mine = dr.approval_expense_ids.filtered(
                lambda r: r.approval_request_line_id == line
            )
            row.remaining_after = (
                line.total_amount
                - sum(others.mapped("amount"))
                - sum(mine.mapped("amount"))
            )

    @api.constrains("amount")
    def _check_amount_positive(self):
        for rec in self:
            if rec.currency_id.compare_amounts(rec.amount, 0) <= 0:
                raise ValidationError(_("จำนวนเงินของค่าใช้จ่ายที่ขอเบิกต้องมากกว่า 0"))
