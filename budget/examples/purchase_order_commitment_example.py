"""
Example: Purchase Order Integration with Budget Commitment Mixin

This example demonstrates the dynamic field approach for budget
commitment integration. Shows how to configure custom field names
and create comprehensive budget workflow integration.

Note: This is an EXAMPLE file for documentation purposes.
To implement this in your module, adapt the code to your specific needs.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderManual(models.Model):
    """
    Purchase Order with Budget Commitment Integration

    This example demonstrates the dynamic field approach for budget
    commitment integration. Shows how to configure custom field names
    and create comprehensive budget workflow integration.
    """
    _name = 'purchase.order.manual'
    _inherit = ['purchase.order', 'budget.commitment.mixin', 'analytic.distribution.mixin']

    # Configure dynamic field names for the mixin
    _commitment_id_field = 'budget_commitment_id'
    _commitment_account_id_field = 'budget_account_id'

    budget_commitment_id = fields.Many2one(
        'budget.commitment',
        string='Budget Commitment',
        readonly=True,
        copy=False,
        help="Related budget commitment for this purchase order"
    )

    budget_account_id = fields.Many2one(
        'budget.account',
        string='Budget Account',
        domain=[('budgetable', '=', True), ('budget_type', '=', 'expense')],
        help="Budget account to be used for commitment"
    )

    def action_check_budget(self):
        """Action to check budget availability"""
        self.ensure_one()

        if not all([
            self.budget_account_id,
            self.activity_analytic_id,
            self.department_analytic_id,
            self.fund_analytic_id,
            self.source_analytic_id,
        ]):
            raise UserError(_("Please specify budget account and all required analytic dimensions"))

        # Check budget availability using dynamic field approach
        result = self._check_budget_availability(
            amount=self.amount_total,
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
        )

        # Show notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Budget Check'),
                'message': result['message'],
                'type': 'success' if result['is_sufficient'] else 'warning',
                'sticky': False,
            }
        }

    def action_reserve_budget(self):
        """Reserve budget by creating commitment"""
        self.ensure_one()

        if self.budget_commitment_id:
            raise UserError(_("Budget has already been reserved for this purchase order"))

        if not self.budget_account_id:
            raise ValidationError(_("Please specify budget account"))

        # Validate required analytic dimensions
        if not all([self.activity_analytic_id, self.department_analytic_id, self.fund_analytic_id, self.source_analytic_id]):
            raise ValidationError(_("Please specify analytic dimensions for budget commitment"))

        # Check budget availability first
        check_result = self._check_budget_availability(
            amount=self.amount_total,
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
        )

        if not check_result['is_sufficient']:
            raise UserError(_("Cannot reserve budget due to insufficient funds: %s") % check_result['message'])

        try:
            # Create commitment using dynamic field approach
            commitment = self._create_budget_commitment(
                amount=self.amount_total,
                activity_analytic_id=self.activity_analytic_id.id,
                department_analytic_id=self.department_analytic_id.id,
                fund_analytic_id=self.fund_analytic_id.id,
                source_analytic_id=self.source_analytic_id.id,
                ref=self.name,
                description=f"Purchase Order: {self.name}\\nVendor: {self.partner_id.name}",
                date=self.date_order,
                auto_reserve=True
            )
            # Note: commitment is automatically stored in budget_commitment_id by the mixin
            self.message_post(body=_("Budget reserved: %s for amount %s") % (commitment.name, self.amount_total))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Budget Reserved'),
                    'message': _('Budget has been successfully reserved for %s') % self.amount_total,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except UserError as e:
            raise UserError(_("Cannot reserve budget: %s") % str(e))

    def button_confirm(self):
        """Confirm purchase order - budget reservation is now separate"""
        # Check if budget reservation is required but not done
        for order in self:
            if not order.budget_commitment_id:
                raise UserError(_(
                    "Please reserve budget first before confirming the purchase order. "
                    "Click 'Reserve Budget' button to proceed."
                ))

        return super().button_confirm()

    def button_cancel(self):
        """Cancel budget commitment when PO is cancelled"""
        for order in self:
            if order.budget_commitment_id:
                try:
                    order._cancel_budget_commitment()  # Uses dynamic field automatically
                    order.message_post(body=_("Budget commitment %s has been cancelled") % order.budget_commitment_id.name)
                except UserError as e:
                    order.message_post(body=_("Warning: Could not cancel budget commitment: %s") % str(e))

        return super().button_cancel()

    def write(self, vals):
        """Override to update commitment amount if PO amount changes"""
        result = super().write(vals)

        if 'amount_total' in vals:
            for order in self:
                if order.budget_commitment_id and order.state == 'purchase':
                    try:
                        # Update commitment amount using dynamic field approach
                        order._update_commitment_amount(order.amount_total)
                        order.message_post(body=_("Budget commitment updated to %s") % order.amount_total)
                    except (UserError, ValidationError) as e:
                        raise UserError(_("Cannot update purchase order amount: %s") % str(e))

        return result

    def action_create_invoice(self):
        """Override to consume budget commitment when invoice is created"""
        result = super().action_create_invoice()

        for order in self:
            if order.budget_commitment_id and order.invoice_ids:
                # Get latest invoice
                invoice = order.invoice_ids[-1]

                # Consume commitment for invoice amount
                try:
                    budget_move = order._consume_commitment(invoice.amount_total, reference=f"Invoice: {invoice.name}")

                    # Link budget move to invoice (if field exists)
                    if hasattr(invoice, 'budget_move_id'):
                        invoice.budget_move_id = budget_move

                    order.message_post(body=_("Budget consumed for invoice %s: %s") % (invoice.name, invoice.amount_total))

                except (UserError, ValidationError) as e:
                    # Log warning but don't block invoice creation
                    order.message_post(body=_("Warning: Could not consume budget commitment: %s") % str(e))

        return result

    def action_view_budget_commitment(self):
        self.ensure_one()
        if not self.budget_commitment_id:
            raise UserError(_("No budget commitment linked to this purchase order"))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Commitment'),
            'res_model': 'budget.commitment',
            'res_id': self.budget_commitment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
