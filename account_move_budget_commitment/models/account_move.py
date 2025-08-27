# -*- coding: utf-8 -*-
# Copyright (C) 2024 KMITL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""
Account Move Budget Integration using budget.commitment.mixin

This module extends account.move with budget commitment functionality
using the proven budget.commitment.mixin pattern.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Account Move with Budget Commitment Integration
    
    Uses budget.commitment.mixin to provide budget integration:
    - Budget availability checking
    - Budget commitment creation and management
    - Automatic budget consumption on posting
    - Integration with KMITL's 4D analytic system
    """
    _inherit = ['account.move', 'budget.commitment.mixin']

    # Configure mixin field names
    _commitment_id_field = 'budget_commitment_id'
    _commitment_account_id_field = 'budget_account_id'

    # Budget Integration Fields
    budget_commitment_id = fields.Many2one(
        'budget.commitment',
        string='Budget Commitment',
        readonly=True,
        copy=False,
        help="Related budget commitment for this journal entry"
    )
    
    budget_account_id = fields.Many2one(
        'budget.account',
        string='Budget Account',
        domain=[('budgetable', '=', True), ('budget_type', '=', 'expense')],
        help="Budget account to be used for commitment"
    )
    
    requires_budget = fields.Boolean(
        string='Requires Budget',
        compute='_compute_requires_budget',
        store=True,
        help="True if this move requires budget commitment"
    )
    
    budget_status = fields.Selection([
        ('none', 'No Budget Required'),
        ('draft', 'Budget Not Reserved'),
        ('reserved', 'Budget Reserved'),
        ('consumed', 'Budget Consumed'),
    ], string='Budget Status', compute='_compute_budget_status', store=True)

    # 4D Analytic Dimensions (from account_analytic_kmitl)
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        domain="[('plan_id.code', '=', 'activities')]",
        help="Activity dimension for budget tracking"
    )
    
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department", 
        domain="[('plan_id.code', '=', 'departments')]",
        help="Department dimension for budget tracking"
    )
    
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        domain="[('plan_id.code', '=', 'funds')]", 
        help="Fund dimension for budget tracking"
    )
    
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        domain="[('plan_id.code', '=', 'sources')]",
        help="Source dimension for budget tracking"
    )

    @api.depends('move_type', 'line_ids.account_id')
    def _compute_requires_budget(self):
        """
        Determine if this move requires budget commitment.
        
        Requires budget if:
        - It's an expense-type move (vendor bill, misc entry with expense lines)
        - Contains expense account lines with debit amounts
        """
        for move in self:
            requires = False
            
            if move.move_type in ['in_invoice', 'in_refund', 'entry']:
                # Check if has expense lines with debit amounts
                expense_lines = move.line_ids.filtered(
                    lambda line: line.account_id.account_type == 'expense' and line.debit > 0
                )
                requires = bool(expense_lines)
                
            move.requires_budget = requires

    @api.depends('requires_budget', 'budget_commitment_id', 'state')
    def _compute_budget_status(self):
        """Compute budget status based on current state."""
        for move in self:
            if not move.requires_budget:
                move.budget_status = 'none'
            elif not move.budget_commitment_id:
                move.budget_status = 'draft'
            elif move.state == 'posted' and move.budget_commitment_id.consumed_amount > 0:
                move.budget_status = 'consumed'
            elif move.budget_commitment_id.state in ['reserved', 'obligated']:
                move.budget_status = 'reserved'
            else:
                move.budget_status = 'draft'

    def action_check_budget(self):
        """Check budget availability using the mixin."""
        self.ensure_one()
        
        if not self.requires_budget:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Budget Check'),
                    'message': _('This move does not require budget commitment.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        if not self._validate_budget_requirements():
            return False

        # Calculate total expense amount
        expense_amount = sum(
            line.debit for line in self.line_ids 
            if line.account_id.account_type == 'expense' and line.debit > 0
        )

        # Check budget availability using mixin
        try:
            result = self._check_budget_availability(
                amount=expense_amount,
                activity_analytic_id=self.activity_analytic_id.id,
                department_analytic_id=self.department_analytic_id.id,
                fund_analytic_id=self.fund_analytic_id.id,
                source_analytic_id=self.source_analytic_id.id,
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Budget Check'),
                    'message': result['message'],
                    'type': 'success' if result['is_sufficient'] else 'warning',
                    'sticky': True if not result['is_sufficient'] else False,
                }
            }
            
        except (UserError, ValidationError) as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Budget Check Error'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_reserve_budget(self):
        """Reserve budget using the mixin."""
        self.ensure_one()
        
        if not self.requires_budget:
            raise UserError(_("This move does not require budget commitment"))
            
        if self.budget_commitment_id:
            raise UserError(_("Budget has already been reserved for this journal entry"))

        if not self._validate_budget_requirements():
            return False

        # Calculate total expense amount
        expense_amount = sum(
            line.debit for line in self.line_ids 
            if line.account_id.account_type == 'expense' and line.debit > 0
        )

        try:
            # Create commitment using mixin
            commitment = self._create_budget_commitment(
                amount=expense_amount,
                activity_analytic_id=self.activity_analytic_id.id,
                department_analytic_id=self.department_analytic_id.id,
                fund_analytic_id=self.fund_analytic_id.id,
                source_analytic_id=self.source_analytic_id.id,
                ref=self.ref or self.name,
                description=f"Journal Entry: {self.name}",
                date=self.date,
                auto_reserve=True
            )
            
            self.message_post(
                body=_("Budget reserved: %s for amount %s") % (commitment.name, expense_amount)
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Budget Reserved'),
                    'message': _('Budget has been successfully reserved for %s') % expense_amount,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except (UserError, ValidationError) as e:
            raise UserError(_("Cannot reserve budget: %s") % str(e))

    def action_post(self):
        """Override posting to consume budget commitments."""
        
        # For moves requiring budget, ensure they have reservations
        moves_requiring_budget = self.filtered('requires_budget')
        for move in moves_requiring_budget:
            if not move.budget_commitment_id:
                raise UserError(_(
                    "Journal entry %s requires budget commitment. "
                    "Please reserve budget first before posting."
                ) % move.name)

        # Post the moves using standard process
        result = super().action_post()
        
        # Consume budget commitments after successful posting
        for move in moves_requiring_budget:
            if move.budget_commitment_id:
                try:
                    expense_amount = sum(
                        line.debit for line in move.line_ids 
                        if line.account_id.account_type == 'expense' and line.debit > 0
                    )
                    
                    # Consume commitment using mixin
                    budget_move = move._consume_commitment(
                        amount=expense_amount,
                        reference=f"Posted Journal Entry: {move.name}"
                    )
                    
                    move.message_post(
                        body=_("Budget consumed: %s") % expense_amount
                    )
                    
                except (UserError, ValidationError) as e:
                    # Log warning but don't block posting
                    _logger.warning(
                        "Could not consume budget commitment for move %s: %s", 
                        move.name, str(e)
                    )
                    move.message_post(
                        body=_("Warning: Could not consume budget commitment: %s") % str(e)
                    )
        
        return result

    def button_cancel(self):
        """Cancel budget commitments when moves are cancelled."""
        for move in self:
            if move.budget_commitment_id:
                try:
                    move._cancel_budget_commitment()
                    move.message_post(
                        body=_("Budget commitment %s has been cancelled") % move.budget_commitment_id.name
                    )
                except (UserError, ValidationError) as e:
                    move.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s") % str(e)
                    )

        return super().button_cancel()

    def button_draft(self):
        """Reset budget commitments when moves are reset to draft."""
        for move in self:
            if move.budget_commitment_id:
                try:
                    move._cancel_budget_commitment()
                    move.message_post(
                        body=_("Budget commitment %s has been cancelled") % move.budget_commitment_id.name
                    )
                except (UserError, ValidationError) as e:
                    move.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s") % str(e)
                    )

        return super().button_draft()

    def _validate_budget_requirements(self):
        """Validate that all required fields for budget operations are set."""
        self.ensure_one()
        
        missing_fields = []
        
        if not self.budget_account_id:
            missing_fields.append(_('Budget Account'))
            
        if not self.activity_analytic_id:
            missing_fields.append(_('Activity'))
            
        if not self.department_analytic_id:
            missing_fields.append(_('Department'))
            
        if not self.fund_analytic_id:
            missing_fields.append(_('Fund'))
            
        if not self.source_analytic_id:
            missing_fields.append(_('Source'))
            
        if missing_fields:
            raise ValidationError(_(
                "Please specify the following required fields for budget operations:\n%s"
            ) % '\n'.join(f"• {field}" for field in missing_fields))
            
        return True

    def action_view_budget_commitment(self):
        """View related budget commitment."""
        self.ensure_one()
        
        if not self.budget_commitment_id:
            raise UserError(_("No budget commitment linked to this journal entry"))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Commitment'),
            'res_model': 'budget.commitment',
            'res_id': self.budget_commitment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }