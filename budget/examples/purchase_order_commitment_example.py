"""
Example: Purchase Order Integration with Budget Commitment Mixin

This example demonstrates the flexible parameter-based approach for integrating
budget.commitment.mixin. This approach provides maximum flexibility by allowing
you to use custom analytic field names and structures without being forced to
inherit from analytic.distribution.mixin.

Note: This is an EXAMPLE file for documentation purposes.
To implement this in your module, adapt the code to your specific needs.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderManual(models.Model):
    """
    Purchase Order with Budget Commitment Integration
    
    This example demonstrates the flexible parameter-based approach for budget
    commitment integration without requiring analytic.distribution.mixin inheritance.
    Shows how to use custom analytic field names and create comprehensive
    budget workflow integration.
    """
    _name = 'purchase.order.manual'
    _inherit = ['purchase.order', 'budget.commitment.mixin']
    
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
    
    # Custom analytic fields (different structure from standard)
    project_activity_id = fields.Many2one(
        'account.analytic.account',
        string='Project Activity',
        domain=[('root_plan_id.code', '=', 'activities')],
        help="Activity dimension for budget tracking"
    )
    
    funding_source_id = fields.Many2one(
        'account.analytic.account',
        string='Funding Source',
        domain=[('root_plan_id.code', '=', 'funds')],
        help="Fund dimension for budget tracking"
    )
    
    responsible_department_id = fields.Many2one(
        'account.analytic.account',
        string='Responsible Department',
        domain=[('root_plan_id.code', '=', 'departments')],
        help="Department dimension for budget tracking"
    )
    
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
        'budget_account_id', 'project_activity_id', 'funding_source_id',
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
                order.project_activity_id,
                order.funding_source_id
            ]):
                order.budget_status = 'not_checked'
                order.budget_available = 0.0
            else:
                # Check budget availability using parameter-based approach
                try:
                    result = order._check_budget_availability(
                        amount=order.amount_total,
                        budget_account_id=order.budget_account_id,
                        activity_analytic_id=order.project_activity_id,
                        fund_analytic_id=order.funding_source_id,
                        department_analytic_id=order.responsible_department_id
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
            self.project_activity_id,
            self.funding_source_id
        ]):
            raise UserError(_(
                "Please specify budget account and all required analytic dimensions"
            ))
        
        # Check budget availability using parameter-based approach
        result = self._check_budget_availability(
            amount=self.amount_total,
            budget_account_id=self.budget_account_id,
            activity_analytic_id=self.project_activity_id,
            fund_analytic_id=self.funding_source_id,
            department_analytic_id=self.responsible_department_id
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
        """Create budget commitment using manual parameters"""
        for order in self:
            if order.budget_account_id and not order.budget_commitment_id:
                
                # Validate required analytic dimensions
                if not all([order.project_activity_id, order.funding_source_id]):
                    raise ValidationError(_(
                        "Please specify activity and funding source for budget commitment"
                    ))
                
                # Check budget availability first
                check_result = order._check_budget_availability(
                    amount=order.amount_total,
                    budget_account_id=order.budget_account_id,
                    activity_analytic_id=order.project_activity_id,
                    fund_analytic_id=order.funding_source_id,
                    department_analytic_id=order.responsible_department_id
                )
                
                if not check_result['is_sufficient']:
                    raise UserError(_(
                        "Cannot confirm purchase order due to insufficient budget: %s"
                    ) % check_result['message'])
                
                try:
                    # Create commitment using manual parameters
                    commitment = order._create_budget_commitment(
                        amount=order.amount_total,
                        budget_account_id=order.budget_account_id,
                        activity_analytic_id=order.project_activity_id,
                        fund_analytic_id=order.funding_source_id,
                        department_analytic_id=order.responsible_department_id,
                        ref=order.name,
                        description=f"Purchase Order: {order.name}\nVendor: {order.partner_id.name}",
                        date=order.date_order,
                        auto_reserve=True
                    )
                    
                    order.budget_commitment_id = commitment
                    
                    order.message_post(
                        body=_(
                            "Budget commitment created: %s for amount %s"
                        ) % (commitment.name, order.amount_total)
                    )
                    
                except UserError as e:
                    raise UserError(_(
                        "Cannot confirm purchase order due to budget constraint: %s"
                    ) % str(e))
        
        return super().button_confirm()
    
    def button_cancel(self):
        """Cancel budget commitment when PO is cancelled"""
        for order in self:
            if order.budget_commitment_id:
                try:
                    self._cancel_budget_commitment(order.budget_commitment_id)
                    order.message_post(
                        body=_("Budget commitment %s has been cancelled") % order.budget_commitment_id.name
                    )
                except UserError as e:
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
                
                # Consume commitment for invoice amount using parameter approach
                try:
                    budget_move = order._consume_commitment(
                        order.budget_commitment_id,
                        invoice.amount_total,
                        activity_analytic_id=order.project_activity_id,
                        fund_analytic_id=order.funding_source_id,
                        department_analytic_id=order.responsible_department_id,
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