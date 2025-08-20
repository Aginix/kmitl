"""
Example: Purchase Order Integration with Budget Commitment Mixin

This example demonstrates how to integrate the budget.commitment.mixin
into a purchase order workflow to automatically create and manage budget
commitments when purchase orders are confirmed.

Requirements:
- Model MUST inherit from 'analytic.distribution.mixin' to provide 4D analytic dimensions
- Model MUST inherit from 'budget.commitment.mixin' for budget API methods

Note: This is an EXAMPLE file for documentation purposes.
To implement this in your module, adapt the code to your specific needs.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    """
    Example: Extending Purchase Order with Budget Commitment Integration
    
    Important: This model inherits both:
    - analytic.distribution.mixin: Provides 4D analytic dimension fields
    - budget.commitment.mixin: Provides budget commitment API methods
    """
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'analytic.distribution.mixin', 'budget.commitment.mixin']
    
    # Link to budget commitment
    budget_commitment_id = fields.Many2one(
        'budget.commitment',
        string='Budget Commitment',
        readonly=True,
        copy=False,
        help="Related budget commitment for this purchase order"
    )
    
    # Budget account field (required for commitment)
    budget_account_id = fields.Many2one(
        'budget.account',
        string='Budget Account',
        domain=[('budgetable', '=', True), ('budget_type', '=', 'expense')],
        help="Budget account to be used for commitment"
    )
    
    # Note: The following analytic dimension fields are automatically provided 
    # by analytic.distribution.mixin:
    # - activity_analytic_id (กิจกรรม)
    # - department_analytic_id (ส่วนงาน)  
    # - fund_analytic_id (กองทุน)
    # - source_analytic_id (แหล่งเงิน)
    
    # Budget status display
    budget_status = fields.Selection(
        selection=[
            ('not_checked', 'Not Checked'),
            ('sufficient', 'Budget Available'),
            ('warning', 'Low Budget'),
            ('insufficient', 'Insufficient Budget'),
            ('committed', 'Budget Committed'),
        ],
        string='Budget Status',
        compute='_compute_budget_status',
        store=True
    )
    
    budget_available = fields.Monetary(
        string='Available Budget',
        compute='_compute_budget_status',
        currency_field='currency_id'
    )
    
    @api.depends(
        'budget_account_id', 'activity_analytic_id', 'fund_analytic_id',
        'amount_total', 'budget_commitment_id', 'state'
    )
    def _compute_budget_status(self):
        """Compute budget status for display"""
        for order in self:
            if order.budget_commitment_id:
                order.budget_status = 'committed'
                order.budget_available = order.budget_commitment_id.remaining_amount
            elif not all([
                order.budget_account_id,
                order.activity_analytic_id,
                order.fund_analytic_id
            ]):
                order.budget_status = 'not_checked'
                order.budget_available = 0.0
            else:
                # Check budget availability using record's analytic fields
                try:
                    result = order._check_budget_availability_from_record(
                        amount=order.amount_total,
                        budget_account_id=order.budget_account_id
                    )
                    order.budget_status = result['status']
                    order.budget_available = result['available']
                except Exception:
                    order.budget_status = 'not_checked'
                    order.budget_available = 0.0
    
    def action_check_budget(self):
        """Action to check budget availability"""
        self.ensure_one()
        
        if not all([
            self.budget_account_id,
            self.activity_analytic_id,
            self.fund_analytic_id
        ]):
            raise UserError(_(
                "Please specify budget account and all required analytic dimensions"
            ))
        
        # Check budget availability using record's analytic fields
        result = self._check_budget_availability_from_record(
            amount=self.amount_total,
            budget_account_id=self.budget_account_id
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
    
    def button_confirm(self):
        """Override to create budget commitment on PO confirmation"""
        for order in self:
            # Check if budget commitment is required
            if order.budget_account_id and not order.budget_commitment_id:
                
                # Validate required fields
                if not all([
                    order.activity_analytic_id,
                    order.fund_analytic_id
                ]):
                    raise ValidationError(_(
                        "Please specify all required analytic dimensions for budget commitment"
                    ))
                
                try:
                    # Create budget commitment using record's analytic fields
                    commitment = order._create_budget_commitment_from_record(
                        amount=order.amount_total,
                        budget_account_id=order.budget_account_id,
                        ref=order.name,
                        description=f"Purchase Order: {order.name}\nVendor: {order.partner_id.name}",
                        date=order.date_order,
                        user_id=order.user_id.id if order.user_id else self.env.user.id,
                        auto_reserve=True
                    )
                    
                    # Link commitment to PO
                    order.budget_commitment_id = commitment
                    
                    # Log activity
                    order.message_post(
                        body=_(
                            "Budget commitment created: <a href='#' data-oe-model='budget.commitment' data-oe-id='%s'>%s</a> for amount %s"
                        ) % (commitment.id, commitment.name, order.amount_total)
                    )
                    
                except UserError as e:
                    raise UserError(_(
                        "Cannot confirm purchase order due to budget constraint:\n%s"
                    ) % str(e))
        
        return super().button_confirm()
    
    def button_cancel(self):
        """Override to cancel budget commitment when PO is cancelled"""
        for order in self:
            if order.budget_commitment_id:
                try:
                    self._cancel_budget_commitment(order.budget_commitment_id)
                    order.message_post(
                        body=_("Budget commitment %s has been cancelled") % order.budget_commitment_id.name
                    )
                except UserError as e:
                    # Log but don't block PO cancellation
                    order.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s") % str(e)
                    )
        
        return super().button_cancel()
    
    def write(self, vals):
        """Override to update commitment amount if PO amount changes"""
        result = super().write(vals)
        
        if 'amount_total' in vals:
            for order in self:
                if order.budget_commitment_id and order.state == 'purchase':
                    try:
                        # Update commitment amount
                        self._update_commitment_amount(
                            order.budget_commitment_id,
                            order.amount_total
                        )
                        order.message_post(
                            body=_("Budget commitment updated to %s") % order.amount_total
                        )
                    except (UserError, ValidationError) as e:
                        raise UserError(_(
                            "Cannot update purchase order amount: %s"
                        ) % str(e))
        
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
                    budget_move = order._consume_commitment_from_record(
                        order.budget_commitment_id,
                        invoice.amount_total,
                        reference=f"Invoice: {invoice.name}"
                    )
                    
                    # Link budget move to invoice (if field exists)
                    if hasattr(invoice, 'budget_move_id'):
                        invoice.budget_move_id = budget_move
                    
                    order.message_post(
                        body=_(
                            "Budget consumed for invoice %s: %s"
                        ) % (invoice.name, invoice.amount_total)
                    )
                    
                except (UserError, ValidationError) as e:
                    # Log warning but don't block invoice creation
                    order.message_post(
                        body=_("Warning: Could not consume budget commitment: %s") % str(e)
                    )
        
        return result
    
    def action_view_budget_commitment(self):
        """Action to view the related budget commitment"""
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


class AccountMove(models.Model):
    """
    Example: Extending Account Move (Invoice) with Budget Integration
    
    Note: account.move already inherits analytic.mixin in standard Odoo,
    so we add analytic.distribution.mixin for the 4D dimension fields.
    """
    _name = 'account.move'
    _inherit = ['account.move', 'analytic.distribution.mixin', 'budget.commitment.mixin']
    
    budget_move_id = fields.Many2one(
        'budget.move',
        string='Budget Move',
        readonly=True,
        help="Related budget move for consumption tracking"
    )
    
    def action_post(self):
        """Override to create budget consumption when invoice is posted"""
        result = super().action_post()
        
        for move in self:
            # Check if this is a vendor bill linked to a PO with commitment
            if move.move_type == 'in_invoice' and hasattr(move, 'purchase_order_id'):
                po = move.purchase_order_id
                if po and po.budget_commitment_id and not move.budget_move_id:
                    try:
                        # Consume from PO commitment using move's record
                        budget_move = move._consume_commitment_from_record(
                            po.budget_commitment_id,
                            move.amount_total,
                            reference=f"Invoice: {move.name}"
                        )
                        move.budget_move_id = budget_move
                        
                        move.message_post(
                            body=_(
                                "Budget consumed from commitment %s: %s"
                            ) % (po.budget_commitment_id.name, move.amount_total)
                        )
                        
                    except Exception as e:
                        # Log but don't block posting
                        move.message_post(
                            body=_("Warning: Could not consume budget: %s") % str(e)
                        )
        
        return result


# Alternative Implementation: Using on Purchase Order Lines
class PurchaseOrderLine(models.Model):
    """
    Example: Budget control at line level with different analytics per line
    """
    _name = 'purchase.order.line'
    _inherit = ['purchase.order.line', 'analytic.distribution.mixin']
    
    # Each line can have its own budget account and analytics
    budget_account_id = fields.Many2one(
        'budget.account',
        string='Budget Account',
        domain=[('budgetable', '=', True), ('budget_type', '=', 'expense')]
    )
    
    def _prepare_account_move_line(self, move=False):
        """Override to pass budget analytics to invoice lines"""
        res = super()._prepare_account_move_line(move)
        
        # Pass analytic dimensions to invoice line
        if self.activity_analytic_id:
            res['activity_analytic_id'] = self.activity_analytic_id.id
        if self.department_analytic_id:
            res['department_analytic_id'] = self.department_analytic_id.id
        if self.fund_analytic_id:
            res['fund_analytic_id'] = self.fund_analytic_id.id
        if self.source_analytic_id:
            res['source_analytic_id'] = self.source_analytic_id.id
            
        return res