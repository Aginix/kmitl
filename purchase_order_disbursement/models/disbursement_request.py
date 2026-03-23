# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = 'disbursement.request'

    reference = fields.Reference(
        selection_add=[('purchase.order', 'Purchase Order')],
        ondelete={'purchase.order': 'set null'},
    )

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        compute="_compute_reference_fields",
        store=True,
        index=True,
        tracking=True,
    )

    # --- Pipeline: Payment tracking ---
    payment_ids = fields.Many2many(
        comodel_name="account.payment",
        compute="_compute_payment_ids",
        string="Payments",
    )
    payment_count = fields.Integer(
        compute="_compute_payment_ids",
        string="Payment Count",
    )
    bill_payment_state = fields.Selection(
        related="bill_id.payment_state",
        string="Bill Payment Status",
    )
    bill_amount_residual = fields.Monetary(
        related="bill_id.amount_residual",
        string="Amount Due",
        currency_field="currency_id",
    )
    hide_register_payment_button = fields.Boolean(
        compute="_compute_hide_register_payment_button",
    )

    @api.depends("reference")
    def _compute_reference_fields(self):
        super()._compute_reference_fields()
        for rec in self:
            if rec.reference and rec.reference._name == 'purchase.order':
                rec.purchase_id = rec.reference
            else:
                rec.purchase_id = False

    def _compute_analytic(self):
        """Merge analytic_distribution from first PO line when reference is a PO."""
        super()._compute_analytic()
        for rec in self:
            if rec.reference and rec.reference._name == 'purchase.order':
                po = rec.reference
                for line in po.order_line:
                    if line.analytic_distribution:
                        rec.analytic_distribution = line.analytic_distribution
                        break

    @api.depends("bill_id")
    def _compute_payment_ids(self):
        Payment = self.env["account.payment"]
        for rec in self:
            payments = Payment
            if rec.bill_id:
                # Reconciled payments (posted & matched)
                payments |= rec.bill_id._get_reconciled_payments()
                # Draft/submitted payments awaiting posting (KMITL flow)
                payments |= Payment.search([
                    ("to_reconcile_payment_line_ids.move_id", "=", rec.bill_id.id),
                ])
            rec.payment_ids = payments
            rec.payment_count = len(payments)

    @api.depends("bill_id", "bill_id.state", "bill_id.payment_state")
    def _compute_hide_register_payment_button(self):
        for rec in self:
            rec.hide_register_payment_button = not (
                rec.bill_id
                and rec.bill_id.state == "posted"
                and rec.bill_id.payment_state in ("not_paid", "partial")
            )

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            raise UserError(_('No Purchase Order linked to this request.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Order'),
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_register_payment(self):
        """Open payment wizard for the linked bill."""
        self.ensure_one()
        if not self.bill_id:
            raise UserError(_("No bill linked. Create a bill first."))
        if self.bill_id.state != "posted":
            raise UserError(_("The bill must be posted before registering a payment."))
        return {
            "name": _("Register Payment"),
            "res_model": "account.payment.register",
            "view_mode": "form",
            "context": {
                "active_model": "account.move",
                "active_ids": [self.bill_id.id],
                "dont_redirect_to_payments": True,
            },
            "target": "new",
            "type": "ir.actions.act_window",
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
