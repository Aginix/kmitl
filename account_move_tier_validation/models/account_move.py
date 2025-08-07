# -*- coding: utf-8 -*-
# Copyright (C) 2024 KMITL
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

"""
Account Move Model Extension with Tier Validation

This module extends the account.move model to add tier validation capabilities,
implementing a 2-step approval workflow for journal entries before they can be posted.
"""

import logging

from odoo import _, api, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Extended AccountMove model with tier validation capabilities.
    
    This class inherits from both 'account.move' and 'tier.validation' to add
    a 2-step approval workflow for journal entries. Journal entries must be
    validated and approved before they can be posted.
    
    Workflow States:
    - draft: Initial state, can be edited
    - under_validation: Waiting for validation/approval
    - validated: All approval tiers completed, ready for posting
    - posted: Final state, journal entry is confirmed
    
    Tier Validation Configuration:
    - _state_from: Starting states that can enter validation (draft)
    - _state_to: Target states after validation (posted)
    - _tier_validation_manual_config: Disables automatic tier configuration
    """
    _name = "account.move"
    _inherit = ["account.move", "tier.validation"]
    
    # Define which states can enter and exit the validation process
    _state_from = ["draft"]  # Only draft entries can start validation
    _state_to = ["posted"]   # Validation leads to posted state
    
    # Disable automatic tier validation configuration
    # This ensures we use the manually defined tier definitions in XML data
    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        """
        Define fields that can be modified while the record is under validation.
        
        This method extends the parent implementation to allow modification of
        invoice lines and journal entry lines during the validation process,
        which may be necessary for validators to make corrections.
        
        Returns:
            list: Field names that can be modified during validation
        """
        res = super(AccountMove, self)._get_under_validation_exceptions()
        # Allow modification of invoice lines and journal entry lines during validation
        res.append(["invoice_line_ids", "line_ids"])
        return res

    def action_post(self):
        """
        Override the standard posting action to enforce tier validation.
        
        This method ensures that journal entries go through the proper validation
        workflow before being posted. The validation process consists of:
        1. Request validation if no reviews exist yet
        2. Check that all validation tiers are completed
        3. Post the entry if fully validated
        
        Returns:
            dict: Action result (notification or standard post action)
        
        Raises:
            ValidationError: If attempting to post without proper validation
        """
        # Check if validation process has been initiated
        if not self.review_ids:
            # Start the validation process
            self.request_validation()
            # Return a user notification instead of posting
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Validation Required"),
                    'message': _("This journal entry requires validation before posting."),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Ensure all validation tiers are completed
        if not self.validated:
            raise ValidationError(
                _("This journal entry must be validated before posting.")
            )
        
        # Proceed with normal posting if validation is complete
        return super().action_post()

    def button_draft(self):
        """
        Override the reset to draft action to restart validation process.
        
        When a journal entry is reset to draft state, any existing validation
        reviews are cleared so the validation process can start fresh when
        the entry is ready to be posted again.
        
        Returns:
            dict: Result from the parent button_draft method
        """
        # Clear any existing validation reviews
        self.restart_validation()
        # Proceed with normal draft reset
        return super().button_draft()
