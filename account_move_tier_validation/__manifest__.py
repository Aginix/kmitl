# -*- coding: utf-8 -*-
# Copyright (C) 2024 KMITL
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Account Move Tier Validation",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "summary": "Tier validation for account moves with 2-step approval process",
    "description": """
Account Move Tier Validation Module

This module implements a 2-step approval workflow for accounting journal entries (account.move)
using the base_tier_validation framework. It ensures financial controls by requiring:

1. Validation step: Users with 'Account Move Validator' role review entries
2. Approval step: Users with 'Account Move Approver' role give final approval

Key Features:
- Prevents posting of journal entries without proper approval
- Implements sequential approval workflow (validate → approve → post)
- Provides user notifications during validation process
- Integrates with Odoo's base tier validation system
- Supports comments during validation/approval steps

Dependencies:
- account: Core Odoo accounting functionality
- base_tier_validation: OCA tier validation framework

Data Loading Order:
1. security/security.xml - Creates security groups for validators and approvers
2. security/ir.model.access.csv - Defines access rights for tier validation objects
3. data/tier_definition_data.xml - Sets up the 2-step validation workflow
    """,
    "author": "KMITL",
    "website": "",
    "license": "LGPL-3",
    "depends": [
        "account",
        "base_tier_validation",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/tier_definition_data.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}