from odoo import _, fields, models
from odoo.exceptions import UserError


class ApprovalRequestFinanceSubmitConfirm(models.TransientModel):
    """Confirmation before handing an approved request to finance
    (approved → to_disburse). Shows a read-only summary — totals, reserved
    budget and the recorded actual-expense rows — so the creator can review
    before submitting."""

    _name = "approval.request.finance.submit.confirm"
    _description = "Confirm Submit to Finance"

    request_id = fields.Many2one(
        "approval.request",
        string="Request",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(related="request_id.name", string="เลขที่คำขอ", readonly=True)
    category_id = fields.Many2one(
        related="request_id.category_id", string="ประเภทคำขอ", readonly=True
    )
    account_fiscal_year_id = fields.Many2one(
        related="request_id.account_fiscal_year_id", string="ปีงบประมาณ", readonly=True
    )
    budget_account_id = fields.Many2one(
        related="request_id.budget_account_id", string="รหัสงบประมาณ", readonly=True
    )
    currency_id = fields.Many2one(related="request_id.currency_id", readonly=True)
    total_amount = fields.Monetary(
        related="request_id.total_amount",
        string="งบตามแผน",
        currency_field="currency_id",
        readonly=True,
    )
    budget_commitment_amount = fields.Monetary(
        related="request_id.budget_commitment_amount",
        string="ยอดจองงบ",
        currency_field="currency_id",
        readonly=True,
    )
    total_actual_amount = fields.Monetary(
        related="request_id.total_actual_amount",
        string="รวมยอดเบิกจริง",
        currency_field="currency_id",
        readonly=True,
    )
    allocation_ids = fields.One2many(
        related="request_id.allocation_ids",
        string="ค่าใช้จ่ายจริง",
        readonly=True,
    )

    def action_confirm(self):
        self.ensure_one()
        self.request_id.action_submit_to_finance()
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "view_mode": "form",
            "res_id": self.request_id.id,
            "target": "current",
        }


class ApprovalRequestFinanceReturnConfirm(models.TransientModel):
    """ตีกลับเพื่อให้แก้ไข (to_disburse → approved) — reason is mandatory and is
    posted in the same chatter message as the state change (via
    _track_set_log_message)."""

    _name = "approval.request.finance.return.confirm"
    _description = "Confirm Finance Return for Editing"

    request_id = fields.Many2one(
        "approval.request",
        string="Request",
        required=True,
        ondelete="cascade",
    )
    reason = fields.Text(string="เหตุผลที่ตีกลับ", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not (self.reason or "").strip():
            raise UserError(_("กรุณากรอกเหตุผลในการตีกลับ"))
        self.request_id._finance_return_for_edit(self.reason)
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "view_mode": "form",
            "res_id": self.request_id.id,
            "target": "current",
        }
