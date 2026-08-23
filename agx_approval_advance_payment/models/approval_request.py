from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # A request may back several loans — one per participant who chose to borrow
    # (ADR-0003). Loans are pulled from the loan side; the request never creates
    # them, so there is no create button here.
    advance_payment_ids = fields.One2many(
        comodel_name="advance.payment",
        inverse_name="approval_request_id",
        string="สัญญายืมเงิน",
        readonly=True,
        copy=False,
    )

    advance_payment_count = fields.Integer(
        compute="_compute_advance_payment_count",
    )

    borrowing_cap = fields.Monetary(
        string="วงเงินยืมของคำขอ",
        compute="_compute_borrowing_headroom",
        help="Reserved budget if there is one, else the plan total.",
    )

    borrowed_amount = fields.Monetary(
        string="ยืมไปแล้ว",
        compute="_compute_borrowing_headroom",
    )

    borrowing_headroom = fields.Monetary(
        string="วงเงินยืมคงเหลือ",
        compute="_compute_borrowing_headroom",
        help="วงเงินของคำขอ หักสัญญายืมทุกใบที่ยังไม่ถูกยกเลิก — สัญญาที่ปิดแล้วยังนับ "
        "เพราะเงินก้อนนั้นออกไปตามคำขอนี้แล้ว",
    )

    has_advance_divergence = fields.Boolean(
        compute="_compute_has_advance_divergence",
    )

    show_create_disbursement_button = fields.Boolean(
        compute="_compute_show_create_disbursement_button",
    )

    @api.depends("advance_payment_ids")
    def _compute_advance_payment_count(self):
        for rec in self:
            rec.advance_payment_count = len(rec.advance_payment_ids)

    @api.depends(
        "budget_commitment_amount",
        "total_amount",
        "advance_payment_ids.loan_amount",
        "advance_payment_ids.state",
    )
    def _compute_borrowing_headroom(self):
        for rec in self:
            cap = rec.budget_commitment_amount or rec.total_amount
            drawn = sum(
                rec.advance_payment_ids.filtered(
                    lambda loan: loan.state != "cancel"
                ).mapped("loan_amount")
            )
            rec.borrowing_cap = cap
            rec.borrowed_amount = drawn
            rec.borrowing_headroom = cap - drawn

    @api.depends(
        "advance_payment_ids.has_expense_divergence",
        "allocation_ids.amount",
        "allocation_ids.advance_payment_id",
    )
    def _compute_has_advance_divergence(self):
        for rec in self:
            rec.has_advance_divergence = any(
                rec.advance_payment_ids.mapped("has_expense_divergence")
            )

    @api.depends("state", "has_active_disbursement")
    def _compute_show_create_disbursement_button(self):
        """เงินยืม rows never enter a disbursement (ADR-0002), so the direct and
        prepaid recipients must not be gated on anyone's loan state (ADR-0003)."""
        for rec in self:
            rec.show_create_disbursement_button = (
                rec.state == "to_disburse" and not rec.has_active_disbursement
            )

    @api.constrains("allocation_ids", "state")
    def _check_advance_rows_have_funding_loan(self):
        """Billing an `advance` row without naming the loan it came out of would
        claim payment from a สัญญายืม that may not exist (ADR-0003)."""
        for rec in self.filtered(lambda r: r.state == "billed"):
            orphans = rec.allocation_ids.filtered(
                lambda a: a.payment_type == "advance" and not a.advance_payment_id
            )
            if orphans:
                raise ValidationError(
                    _(
                        "กรุณาระบุสัญญายืมเงินที่เป็นแหล่งเงินของทุกแถวเงินยืมก่อนส่งเบิก: %s"
                    )
                    % ", ".join(orphans.mapped("partner_id.name"))
                )

    def action_cancel(self):
        """A request may not be cancelled while it still backs a live loan: the
        cash is out and the debt is the borrower's to clear (ADR-0003). No
        cascade in either direction."""
        for rec in self:
            live = rec.advance_payment_ids.filtered(
                lambda loan: loan.state not in ("cancel", "done")
            )
            if live:
                raise UserError(
                    _(
                        "ยกเลิกคำขอนี้ไม่ได้ เพราะยังมีสัญญายืมเงินผูกอยู่: %(loans)s"
                        " — ผู้ยืมต้องปิดหรือยกเลิกสัญญาของตนเองก่อน"
                        " (ทริปที่ล่มคือรายงานค่าใช้จ่ายยอด 0 แล้วคืนเงินทั้งก้อน)",
                        loans=", ".join(live.mapped("name")),
                    )
                )
        return super().action_cancel()

    def action_view_advance_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("สัญญายืมเงิน"),
            "res_model": "advance.payment",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.advance_payment_ids.ids)],
            "target": "current",
        }
