# Security Configuration

This directory contains the security configuration files for the Account Move Tier Validation module.

## Files

### security.xml
Defines security groups for the tier validation system:
- `group_account_move_validator`: First tier validation users
- `group_account_move_approver`: Second tier approval users (inherits validator permissions)

### ir.model.access.csv
Access Control Rules for Account Move Tier Validation

This file defines the specific permissions for tier validation objects, controlling who can read, write, create, or delete tier definitions and tier reviews.

**Permission Structure:**
- Validators: Can create and modify review records but only read tier definitions
- Approvers: Have full control over both tier definitions and review records

**Security Model:**
- `tier.definition`: Configuration records defining the validation workflow
- `tier.review`: Individual review instances created during validation process

**Permission Codes:** read(1/0), write(1/0), create(1/0), unlink(1/0)

**Access Rules:**
1. `access_tier_definition_account_move_validator`: Validators can read tier definitions but cannot modify workflow configuration
2. `access_tier_definition_account_move_approver`: Approvers have full control over tier definitions (can configure workflows)
3. `access_tier_review_account_move_validator`: Validators can create and modify their own review records during validation
4. `access_tier_review_account_move_approver`: Approvers can create and modify review records for both validation and approval tiers