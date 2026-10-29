from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class DisbursementRequest(models.Model):
    """A request of payment type เงินยืม is a ใบเบิกชดใช้เงินยืม: it books
    spending already paid out of a loan, pays the borrower nothing, and clears
    the loan when its budget is consumed (ADR-0032).

    The requester need not hold any loan right: the loan is read under sudo
    (picker, related display, checks).
    """

    _inherit = "disbursement.request"

    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="เลขที่สัญญายืมเงิน",
        domain="[('state', '=', 'in_progress'),"
        " ('operating_unit_id', '=', operating_unit_id)]",
        index=True,
        copy=False,
        ondelete="restrict",
        tracking=True,
    )

    # Related fields are read as sudo: the requester sees the loan's figures
    # without any right on the loan.
    advance_payment_employee_id = fields.Many2one(
        related="advance_payment_id.employee_id", string="ผู้ยืม"
    )
    advance_payment_loan_type_id = fields.Many2one(
        related="advance_payment_id.loan_type_id", string="ประเภทเงินยืม"
    )
    advance_payment_loan_amount = fields.Monetary(
        related="advance_payment_id.loan_amount", string="จำนวนเงินยืม"
    )
    advance_payment_actual_expense_amount = fields.Monetary(
        related="advance_payment_id.actual_expense_amount", string="ส่งใช้คืน"
    )
    advance_payment_amount_remaining = fields.Monetary(
        related="advance_payment_id.amount_remaining", string="คงเหลือ"
    )
    advance_payment_effective_date = fields.Date(
        related="advance_payment_id.effective_date", string="วันที่เป็นลูกหนี้"
    )
    advance_payment_return_due_date = fields.Date(
        related="advance_payment_id.return_due_date", string="วันที่ครบกำหนด"
    )
    advance_payment_return_due_status = fields.Selection(
        related="advance_payment_id.return_due_status", string="สถานะวันครบกำหนด"
    )

    def read(self, fields=None, load="_classic_read"):
        """The loan reads as in its picker: "<contract number> — <borrower>"
        (advance.payment.name_get)."""
        return super(
            DisbursementRequest, self.with_context(advance_payment_picker=True)
        ).read(fields=fields, load=load)

    @api.onchange("payment_type")
    def _onchange_payment_type_advance_payment(self):
        if self.payment_type != "advance":
            self.advance_payment_id = False

    @api.onchange("advance_payment_id")
    def _onchange_advance_payment_id(self):
        """The borrower is the only payee: type the request after them and
        put them on every line."""
        partner = self.advance_payment_id.sudo().partner_id
        if not partner:
            return
        if partner.partner_type_id:
            self.partner_type_id = partner.partner_type_id
        if self.line_ids:
            self.line_ids.update({"partner_id": partner.id})
        else:
            self.line_ids = [Command.create({"partner_id": partner.id})]

    @api.constrains("payment_type", "advance_payment_id")
    def _check_advance_payment_payment_type(self):
        for rec in self:
            if rec.advance_payment_id and rec.payment_type != "advance":
                raise ValidationError(
                    _("Only a request of payment type Advance may name a loan.")
                )
            rec.line_ids._check_advance_payment_borrower()

    def action_submit(self):
        for rec in self:
            if rec.payment_type == "advance" and not rec.advance_payment_id:
                raise UserError(
                    _(
                        "An advance request must name the loan (เลขที่สัญญายืมเงิน) it clears."
                    )
                )
        return super().action_submit()

    def _check_advance_payment_clearable(self):
        """The loan must still be owed (ค้างชำระ) and owe at least this
        request's amount."""
        self.ensure_one()
        loan = self.advance_payment_id.sudo()
        if loan.state != "in_progress":
            raise UserError(
                _(
                    "Loan %(loan)s is not outstanding (ค้างชำระ): it cannot be cleared.",
                    loan=loan.contract_number or loan.name,
                )
            )
        if (
            float_compare(
                self.amount_total,
                loan.amount_remaining,
                precision_rounding=self.currency_id.rounding,
            )
            > 0
        ):
            raise UserError(
                _(
                    "The request amount %(amount)s exceeds what loan %(loan)s "
                    "still owes (%(remaining)s).",
                    amount=self.amount_total,
                    loan=loan.contract_number or loan.name,
                    remaining=loan.amount_remaining,
                )
            )

    def action_consume_budget(self):
        """ตัดงบ clears the loan by the consumed amount. Wrapped here rather
        than in ``_action_approve_budget`` so every consume path (a direct
        claim's too) is covered whatever the module order."""
        for rec in self:
            if (
                rec.advance_payment_id
                and rec.consumes_budget
                and not rec.budget_consumed_amount
            ):
                rec._check_advance_payment_clearable()
        res = super().action_consume_budget()
        for rec in self.filtered("advance_payment_id"):
            rec.advance_payment_id.sudo()._sync_cleared_amount(rec)
        return res

    def _on_cancel(self):
        """A cancelled request gives back what it cleared (core resets its
        consumed amount)."""
        super()._on_cancel()
        for rec in self.filtered("advance_payment_id"):
            rec.advance_payment_id.sudo()._sync_cleared_amount(rec)
