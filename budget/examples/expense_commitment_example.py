"""
Example: HR Expense Integration with Budget Commitment Mixin

This example demonstrates how to integrate the budget.commitment.mixin
into an expense claim workflow to automatically create and manage budget
commitments for employee expenses.

Requirements:
- Model MUST inherit from 'analytic.distribution.mixin' to provide 4D analytic dimensions
- Model MUST inherit from 'budget.commitment.mixin' for budget API methods

Note: This is an EXAMPLE file for documentation purposes.
To implement this in your module, adapt the code to your specific needs.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrExpenseSheet(models.Model):
    """
    Example: Extending HR Expense Sheet with Budget Commitment Integration
    
    Important: This model inherits both:
    - analytic.distribution.mixin: Provides 4D analytic dimension fields
    - budget.commitment.mixin: Provides budget commitment API methods
    """
    _name = 'hr.expense.sheet'
    _inherit = ['hr.expense.sheet', 'analytic.distribution.mixin', 'budget.commitment.mixin']
    
    # Link to budget commitment
    budget_commitment_id = fields.Many2one(
        'budget.commitment',
        string='Budget Commitment',
        readonly=True,
        copy=False,
        help="Related budget commitment for this expense"
    )
    
    # Budget account field
    budget_account_id = fields.Many2one(
        'budget.account',
        string='Budget Account',
        compute='_compute_budget_account',
        store=True,
        readonly=False,
        domain=[('budgetable', '=', True), ('budget_type', '=', 'expense')]
    )
    
    # Note: The following analytic dimension fields are automatically provided 
    # by analytic.distribution.mixin:
    # - activity_analytic_id (กิจกรรม)
    # - department_analytic_id (ส่วนงาน) - can be auto-computed from employee
    # - fund_analytic_id (กองทุน)
    # - source_analytic_id (แหล่งเงิน)
    
    require_budget_commitment = fields.Boolean(
        string='Require Budget Commitment',
        default=True,
        help="If checked, budget commitment will be required for approval"
    )
    
    budget_status_display = fields.Char(
        string='Budget Status',
        compute='_compute_budget_display',
        store=True
    )
    
    @api.depends('expense_line_ids.product_id')
    def _compute_budget_account(self):
        """Auto-detect budget account from expense lines"""
        for sheet in self:
            if not sheet.budget_account_id and sheet.expense_line_ids:
                # Try to get from first expense line's product
                first_line = sheet.expense_line_ids[0]
                if hasattr(first_line.product_id, 'budget_account_id'):
                    sheet.budget_account_id = first_line.product_id.budget_account_id
    
    @api.depends('employee_id')
    def _compute_department(self):
        """Auto-set department from employee"""
        for sheet in self:
            if sheet.employee_id and sheet.employee_id.department_id:
                # Map HR department to analytic department
                department_mapping = self.env['ir.config_parameter'].sudo().get_param(
                    'budget.department_mapping', {}
                )
                if sheet.employee_id.department_id.id in department_mapping:
                    sheet.department_analytic_id = department_mapping[sheet.employee_id.department_id.id]
    
    @api.depends('budget_commitment_id', 'state')
    def _compute_budget_display(self):
        """Compute budget status for display"""
        for sheet in self:
            if sheet.budget_commitment_id:
                commitment = sheet.budget_commitment_id
                sheet.budget_status_display = _(
                    "Committed: %s (Remaining: %s)"
                ) % (
                    "{:,.2f}".format(commitment.amount),
                    "{:,.2f}".format(commitment.remaining_amount)
                )
            elif sheet.state in ['draft', 'submit']:
                sheet.budget_status_display = _("Not yet committed")
            else:
                sheet.budget_status_display = _("No commitment")
    
    def action_submit_sheet(self):
        """Override to check budget before submission"""
        for sheet in self:
            if sheet.require_budget_commitment:
                # Validate budget fields
                if not all([
                    sheet.budget_account_id,
                    sheet.activity_analytic_id,
                    sheet.fund_analytic_id
                ]):
                    raise ValidationError(_(
                        "Please specify budget account and all required analytic dimensions"
                    ))
                
                # Check budget availability
                result = sheet._check_budget_availability({
                    'amount': sheet.total_amount,
                    'account_id': sheet.budget_account_id.id,
                    'activity_analytic_id': sheet.activity_analytic_id.id,
                    'department_analytic_id': sheet.department_analytic_id.id if sheet.department_analytic_id else False,
                    'fund_analytic_id': sheet.fund_analytic_id.id,
                    'source_analytic_id': sheet.source_analytic_id.id if sheet.source_analytic_id else False,
                })
                
                if not result['is_sufficient']:
                    raise UserError(_(
                        "Cannot submit expense: %s\n"
                        "Please contact your manager or accounting department."
                    ) % result['message'])
        
        return super().action_submit_sheet()
    
    def _do_approve(self):
        """Override to create budget commitment on approval"""
        for sheet in self:
            if sheet.require_budget_commitment and not sheet.budget_commitment_id:
                try:
                    # Create budget commitment
                    commitment = sheet._create_budget_commitment({
                        'amount': sheet.total_amount,
                        'ref': sheet.name,
                        'description': self._prepare_commitment_description(sheet),
                        'account_id': sheet.budget_account_id.id,
                        'activity_analytic_id': sheet.activity_analytic_id.id,
                        'department_analytic_id': sheet.department_analytic_id.id if sheet.department_analytic_id else False,
                        'fund_analytic_id': sheet.fund_analytic_id.id,
                        'source_analytic_id': sheet.source_analytic_id.id if sheet.source_analytic_id else False,
                        'date': sheet.accounting_date or fields.Date.today(),
                        'user_id': sheet.user_id.id,
                    }, auto_reserve=True)
                    
                    sheet.budget_commitment_id = commitment
                    
                    # Log activity
                    sheet.message_post(
                        body=_(
                            "Budget commitment created: <a href='#' data-oe-model='budget.commitment' data-oe-id='%s'>%s</a> for amount %s"
                        ) % (commitment.id, commitment.name, sheet.total_amount)
                    )
                    
                except UserError as e:
                    raise UserError(_(
                        "Cannot approve expense due to budget constraint:\n%s"
                    ) % str(e))
        
        return super()._do_approve()
    
    def _prepare_commitment_description(self, sheet):
        """Prepare commitment description from expense details"""
        lines_desc = []
        for line in sheet.expense_line_ids[:3]:  # First 3 lines
            lines_desc.append(f"- {line.name}: {line.total_amount}")
        
        if len(sheet.expense_line_ids) > 3:
            lines_desc.append(f"... and {len(sheet.expense_line_ids) - 3} more items")
        
        return _(
            "Expense Report: %(name)s\n"
            "Employee: %(employee)s\n"
            "Period: %(date)s\n"
            "Details:\n%(lines)s"
        ) % {
            'name': sheet.name,
            'employee': sheet.employee_id.name,
            'date': sheet.accounting_date or sheet.create_date.date(),
            'lines': '\n'.join(lines_desc)
        }
    
    def action_sheet_move_create(self):
        """Override to consume budget when journal entry is created"""
        result = super().action_sheet_move_create()
        
        for sheet in self:
            if sheet.budget_commitment_id and sheet.account_move_id:
                try:
                    # Consume commitment
                    budget_move = self._consume_commitment(
                        sheet.budget_commitment_id,
                        sheet.total_amount,
                        reference=f"Expense Payment: {sheet.name}"
                    )
                    
                    # Link budget move to account move if possible
                    if hasattr(sheet.account_move_id, 'budget_move_id'):
                        sheet.account_move_id.budget_move_id = budget_move
                    
                    sheet.message_post(
                        body=_(
                            "Budget consumed for expense payment: %s"
                        ) % sheet.total_amount
                    )
                    
                except Exception as e:
                    # Log warning but don't block
                    sheet.message_post(
                        body=_("Warning: Could not consume budget: %s") % str(e)
                    )
        
        return result
    
    def refuse_sheet(self, reason):
        """Override to cancel budget commitment when expense is refused"""
        for sheet in self:
            if sheet.budget_commitment_id:
                try:
                    self._cancel_budget_commitment(sheet.budget_commitment_id)
                    sheet.message_post(
                        body=_("Budget commitment cancelled due to expense refusal")
                    )
                except Exception as e:
                    # Log but don't block refusal
                    sheet.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s") % str(e)
                    )
        
        return super().refuse_sheet(reason)
    
    def action_view_budget_commitment(self):
        """Action to view the related budget commitment"""
        self.ensure_one()
        if not self.budget_commitment_id:
            raise UserError(_("No budget commitment linked to this expense"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Commitment'),
            'res_model': 'budget.commitment',
            'res_id': self.budget_commitment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_check_budget_availability(self):
        """Manual action to check budget availability"""
        self.ensure_one()
        
        if not all([
            self.budget_account_id,
            self.activity_analytic_id,
            self.fund_analytic_id
        ]):
            raise UserError(_(
                "Please specify budget account and all required analytic dimensions"
            ))
        
        result = self._check_budget_availability({
            'amount': self.total_amount,
            'account_id': self.budget_account_id.id,
            'activity_analytic_id': self.activity_analytic_id.id,
            'department_analytic_id': self.department_analytic_id.id if self.department_analytic_id else False,
            'fund_analytic_id': self.fund_analytic_id.id,
            'source_analytic_id': self.source_analytic_id.id if self.source_analytic_id else False,
        })
        
        # Show result
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Budget Availability Check'),
                'message': _(
                    "%(message)s\n"
                    "Available: %(available)s\n"
                    "Required: %(required)s"
                ) % {
                    'message': result['message'],
                    'available': "{:,.2f}".format(result['available']),
                    'required': "{:,.2f}".format(result['requested'])
                },
                'type': 'success' if result['is_sufficient'] else 'warning',
                'sticky': False,
            }
        }


class HrExpense(models.Model):
    """
    Example: Individual expense line can override budget analytics
    """
    _name = 'hr.expense'
    _inherit = 'hr.expense'
    
    # Allow override at line level
    budget_account_id = fields.Many2one(
        'budget.account',
        string='Budget Account',
        domain=[('budgetable', '=', True), ('budget_type', '=', 'expense')],
        help="Override budget account for this expense line"
    )
    
    activity_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Activity',
        domain=[('root_plan_id.code', '=', 'activities')],
        help="Override activity for this expense line"
    )
    
    def _get_expense_account_source(self):
        """Override to map to budget account if specified"""
        self.ensure_one()
        if self.budget_account_id:
            # Map budget account to GL account
            if hasattr(self.budget_account_id, 'account_id'):
                return self.budget_account_id.account_id
        return super()._get_expense_account_source()