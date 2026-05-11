# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    pipeline_status = fields.Selection(
        selection_add=[
            ("payment_draft", "Payment Draft"),
            ("payment_posted", "Payment Posted"),
            ("done", "Done"),
        ],
        ondelete={
            "payment_draft": "set default",
            "payment_posted": "set default",
            "done": "set default",
        },
    )

    payment_ids = fields.Many2many(
        comodel_name="account.payment",
        compute="_compute_payment_ids",
        string="Payments",
    )
    payment_count = fields.Integer(
        compute="_compute_payment_ids",
        string="Payment Count",
    )
    payment_status_display = fields.Char(
        string="Payment Status",
        compute="_compute_payment_ids",
    )
    payment_move_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_payment_ids",
        string="Payment Journal Entries",
    )
    payment_move_count = fields.Integer(
        compute="_compute_payment_ids",
        string="Payment Move Count",
    )

    @api.depends("bill_ids", "bill_ids.state", "bill_ids.payment_state")
    def _compute_payment_ids(self):
        Payment = self.env["account.payment"]
        for rec in self:
            payments = Payment
            for bill in rec.bill_ids:
                payments |= bill._get_reconciled_payments()
                payments |= Payment.search([
                    ("to_reconcile_payment_line_ids.move_id", "=", bill.id),
                ])
            active_payments = payments.filtered(lambda p: p.state != "cancel")
            rec.payment_ids = active_payments
            total = len(active_payments)
            rec.payment_count = total
            posted = len(
                active_payments.filtered(lambda p: p.state == "posted")
            )
            rec.payment_status_display = (
                _("จ่ายแล้ว %s/%s", posted, total) if total else ""
            )
            payment_moves = active_payments.mapped("move_id")
            rec.payment_move_ids = payment_moves
            rec.payment_move_count = len(payment_moves)

    @api.depends(
        "bill_ids",
        "bill_ids.state",
        "bill_ids.payment_state",
        "payment_ids",
        "payment_ids.state",
    )
    def _compute_pipeline_status(self):
        super()._compute_pipeline_status()
        Payment = self.env["account.payment"]
        for rec in self:
            if rec.state != "approved":
                continue
            active_bills = rec.bill_ids.filtered(lambda b: b.state != "cancel")
            if not active_bills:
                continue
            if all(b.payment_state == "paid" for b in active_bills):
                rec.pipeline_status = "done"
                continue
            all_payments = Payment
            for bill in active_bills:
                all_payments |= bill._get_reconciled_payments()
                all_payments |= Payment.search([
                    ("to_reconcile_payment_line_ids.move_id", "=", bill.id),
                ])
            active_payments = all_payments.filtered(
                lambda p: p.state != "cancel"
            )
            if active_payments.filtered(lambda p: p.state == "posted"):
                rec.pipeline_status = "payment_posted"
            elif active_payments:
                rec.pipeline_status = "payment_draft"

    def action_cancel(self):
        """Block cancel if any payment exists for the linked bills."""
        for record in self:
            if record.state == "cancel":
                continue
            if record.bill_ids and record.payment_ids:
                raise UserError(
                    _(
                        "Cannot cancel: there are payments linked to bills. "
                        "Remove payments first."
                    )
                )
        return super().action_cancel()

    def action_create_payment(self):
        """Create draft payments directly from DR, one per posted unpaid bill."""
        self.ensure_one()
        unpaid_bills = self.bill_ids.filtered(
            lambda b: b.state == "posted"
            and b.payment_state in ("not_paid", "partial")
        )
        if not unpaid_bills:
            raise UserError(_("No posted unpaid bills to pay."))

        journal = self.env["account.journal"].search(
            [
                ("type", "=", "bank"),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )
        if not journal:
            raise UserError(
                _("No bank journal found for company %s.")
                % self.company_id.name
            )
        payment_type = self.env.ref(
            "finance_kmitl.payment_type_normal_outbound",
            raise_if_not_found=False,
        )

        payments = self.env["account.payment"]
        for bill in unpaid_bills:
            payable_lines = bill.line_ids.filtered(
                lambda l: l.account_type == "liability_payable"
                and not l.reconciled
            )
            amount = abs(bill.amount_residual)

            wht_lines = bill.line_ids.filtered("wht_tax_id")
            write_off_line_vals = []
            if wht_lines:
                deduction_list, amount_wht = (
                    wht_lines._prepare_deduction_list(
                        fields.Date.context_today(self),
                        bill.currency_id,
                    )
                )
                if deduction_list and amount_wht:
                    amount -= amount_wht
                    for deduct in deduction_list:
                        write_off_line_vals.append({
                            "name": deduct["name"],
                            "account_id": deduct["account_id"],
                            "partner_id": bill.partner_id.id,
                            "currency_id": bill.currency_id.id,
                            "amount_currency": -deduct["amount"],
                            "balance": -deduct["amount"],
                            "wht_tax_id": deduct["wht_tax_id"],
                            "tax_base_amount": deduct["wht_amount_base"],
                        })

            payment_vals = {
                "partner_id": bill.partner_id.id,
                "amount": amount,
                "currency_id": bill.currency_id.id,
                "journal_id": journal.id,
                "payment_type": "outbound",
                "partner_type": "supplier",
                "ref": _("%s - %s", self.name, bill.name),
                "analytic_distribution": bill.analytic_distribution,
            }
            if write_off_line_vals:
                payment_vals["write_off_line_vals"] = write_off_line_vals
            if payment_type:
                payment_vals["kmitl_payment_type_id"] = payment_type.id
            if bill.budget_commitment_id:
                payment_vals["budget_commitment_id"] = (
                    bill.budget_commitment_id.id
                )
            if bill.budget_account_id:
                payment_vals["budget_account_id"] = bill.budget_account_id.id

            payment = self.env["account.payment"].create(payment_vals)
            payment.to_reconcile_payment_line_ids = payable_lines
            if bill.analytic_distribution:
                payment.move_id.line_ids.write(
                    {"analytic_distribution": bill.analytic_distribution}
                )
            payments |= payment

        for payment in payments:
            pay_link = (
                "/web#id=%d&model=account.payment&view_type=form" % payment.id
            )
            self.message_post(
                body=_(
                    'Payment <a href="%(link)s" target="_blank">'
                    "%(name)s</a> created for %(partner)s.",
                    link=pay_link,
                    name=payment.name,
                    partner=payment.partner_id.name,
                ),
                subtype_xmlid="mail.mt_note",
            )

        if len(payments) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.payment",
                "res_id": payments.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Payments"),
            "res_model": "account.payment",
            "domain": [("id", "in", payments.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def action_view_payments(self):
        """Open related payment(s)."""
        self.ensure_one()
        if self.payment_count == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Payment"),
                "res_model": "account.payment",
                "res_id": self.payment_ids.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Payments"),
            "res_model": "account.payment",
            "domain": [("id", "in", self.payment_ids.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def action_view_payment_moves(self):
        """Open journal entries linked to payments."""
        self.ensure_one()
        moves = self.payment_move_ids
        if len(moves) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Journal Entry"),
                "res_model": "account.move",
                "res_id": moves.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการล้างหนี้"),
            "res_model": "account.move",
            "domain": [("id", "in", moves.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }
