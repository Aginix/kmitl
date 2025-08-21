# Budget Commitment API Documentation

This document describes the Budget Commitment Mixin API, a standardized interface that allows any Odoo module to integrate with the budget commitment system without direct dependencies.

## Overview

The `budget.commitment.mixin` provides a clean, dynamic field API for:
- Creating budget commitments with proper validation
- Checking budget availability before making commitments
- Managing commitment lifecycle (reserve, consume, cancel, close)
- Tracking budget consumption through invoice and payment workflows
- Dynamic field configuration for maximum flexibility

## Integration Methods

The mixin uses a dynamic field approach where you configure field names and the mixin automatically accesses the correct fields from your model.

### Basic Usage

```python
class PurchaseOrder(models.Model):
    _inherit = ['purchase.order', 'budget.commitment.mixin']
    
    # Configure dynamic field names for the mixin
    _commitment_id_field = 'budget_commitment_id'
    _commitment_account_id_field = 'budget_account_id'
    
    budget_commitment_id = fields.Many2one('budget.commitment')
    budget_account_id = fields.Many2one('budget.account')
    
    # Custom analytic fields
    project_activity_id = fields.Many2one('account.analytic.account')
    funding_source_id = fields.Many2one('account.analytic.account')
    
    def action_reserve_budget(self):
        # Budget account is automatically accessed from dynamic field
        commitment = self._create_budget_commitment(
            amount=self.amount_total,
            activity_analytic_id=self.project_activity_id,
            fund_analytic_id=self.funding_source_id
        )
        # Commitment is automatically stored in budget_commitment_id
```

## Dynamic Field Configuration

Configure these class attributes to customize field names:

- `_commitment_id_field`: Name of the field linking to `budget.commitment` (default: 'budget_commitment_id')
- `_commitment_account_id_field`: Name of the field linking to `budget.account` (default: 'budget_account_id')

## API Methods

### Creation Methods

#### `_create_budget_commitment(amount, activity_analytic_id, fund_analytic_id, **kwargs)`

Creates a budget commitment using the dynamic budget account field.

**Parameters:**
- `amount` (float): Amount to commit - Required
- `activity_analytic_id`: Activity dimension (record or ID) - Required
- `fund_analytic_id`: Fund dimension (record or ID) - Required
- `department_analytic_id`: Department dimension (record or ID) - Optional
- `source_analytic_id`: Source dimension (record or ID) - Optional
- `ref` (str, optional): Reference for the commitment (defaults to record name)
- `description` (str, optional): Description text
- `auto_reserve` (bool, optional): Automatically reserve the commitment (default: True)
- Additional kwargs: `date`, `user_id`, `company_id`, `date_range_fy_id`

**Returns:** `budget.commitment` record (also automatically stored in dynamic commitment field)

**Example:**
```python
# Budget account is automatically retrieved from dynamic field
commitment = self._create_budget_commitment(
    amount=5000.00,
    activity_analytic_id=activity_record,
    fund_analytic_id=fund_record,
    department_analytic_id=department_record,
    ref=f"PO/{self.name}",
    auto_reserve=True
)
# Commitment is automatically stored in self.budget_commitment_id
```

### Validation Methods

#### `_check_budget_availability(amount, activity_analytic_id, fund_analytic_id, **kwargs)`

Checks budget availability using the dynamic budget account field.

**Parameters:**
- `amount` (float): Amount to check
- `activity_analytic_id`: Activity dimension (record or ID) - Required
- `fund_analytic_id`: Fund dimension (record or ID) - Required
- `department_analytic_id`: Department dimension (record or ID) - Optional
- `source_analytic_id`: Source dimension (record or ID) - Optional
- `**kwargs`: Additional optional fields

**Returns:** Dictionary with budget availability information

**Example:**
```python
# Budget account is automatically retrieved from dynamic field
result = self._check_budget_availability(
    amount=self.total_amount,
    activity_analytic_id=self.project_activity,
    fund_analytic_id=self.funding_source
)

if not result['is_sufficient']:
    raise UserError(f"Insufficient budget: {result['message']}")
```

### Consumption Methods

#### `_consume_commitment(amount, reference=None, commitment=None)`

Consumes budget from a commitment. If no commitment is provided, uses the dynamic commitment field.

**Parameters:**
- `amount` (float): Amount to consume
- `reference` (str, optional): Reference for the consumption
- `commitment` (budget.commitment, optional): Commitment to consume from (uses dynamic field if None)

**Returns:** `budget.move` record

**Example:**
```python
# Consume budget when invoice is paid - uses dynamic field automatically
budget_move = self._consume_commitment(
    invoice.amount_total,
    reference=f"Invoice: {invoice.number}"
)
```

### Management Methods

#### `_cancel_budget_commitment(commitment=None)`

Cancels a commitment and releases the reserved budget. If no commitment is provided, uses the dynamic commitment field.

**Parameters:**
- `commitment` (budget.commitment, optional): Commitment to cancel (uses dynamic field if None)

**Returns:** Boolean (True if successful)

**Example:**
```python
# Cancel commitment using dynamic field automatically
if self.state == 'cancel':
    self._cancel_budget_commitment()
```

#### `_close_budget_commitment(commitment=None)`

Marks a commitment as done, releasing any unused budget.

**Parameters:**
- `commitment` (budget.commitment, optional): Commitment to close (uses dynamic field if None)

**Returns:** Boolean (True if successful)

#### `_update_commitment_amount(new_amount, commitment=None)`

Updates the commitment amount with validation. If no commitment is provided, uses the dynamic commitment field.

**Parameters:**
- `new_amount` (float): New commitment amount
- `commitment` (budget.commitment, optional): Commitment to update (uses dynamic field if None)

**Returns:** Boolean (True if successful)

**Example:**
```python
# Update commitment when order amount changes - uses dynamic field automatically
if self.state == 'confirmed':
    self._update_commitment_amount(self.new_total_amount)
```

### Helper Methods

#### `_get_commitment_field_value(field_name)`

Gets the value of a dynamic commitment field.

**Parameters:**
- `field_name` (str): 'commitment_id' or 'account_id'

**Returns:** Field value or False

#### `_set_commitment_field_value(field_name, value)`

Sets the value of a dynamic commitment field.

**Parameters:**
- `field_name` (str): 'commitment_id'
- `value`: Value to set

## Complete Integration Example

### Purchase Order with Dynamic Field Configuration

```python
class PurchaseOrder(models.Model):
    _inherit = ['purchase.order', 'budget.commitment.mixin']
    
    # Configure dynamic field names for the mixin
    _commitment_id_field = 'budget_commitment_id'
    _commitment_account_id_field = 'budget_account_id'
    
    budget_commitment_id = fields.Many2one('budget.commitment')
    budget_account_id = fields.Many2one('budget.account')
    
    # Custom analytic fields
    project_activity_id = fields.Many2one('account.analytic.account')
    funding_source_id = fields.Many2one('account.analytic.account')
    department_id = fields.Many2one('account.analytic.account')
    
    def action_reserve_budget(self):
        """Reserve budget using dynamic fields"""
        self.ensure_one()
        if self._get_commitment_field_value('commitment_id'):
            raise UserError(_("Budget already reserved"))
        
        # Budget account automatically retrieved from dynamic field
        commitment = self._create_budget_commitment(
            amount=self.amount_total,
            activity_analytic_id=self.project_activity_id,
            fund_analytic_id=self.funding_source_id,
            department_analytic_id=self.department_id,
            ref=self.name,
            auto_reserve=True
        )
        # Commitment automatically stored in budget_commitment_id
    
    def button_confirm(self):
        """Confirm order - check budget is reserved first"""
        for order in self:
            if order._get_commitment_field_value('account_id') and not order._get_commitment_field_value('commitment_id'):
                raise UserError(_("Please reserve budget first"))
        return super().button_confirm()
```

## Error Handling

The mixin provides comprehensive error handling:

```python
from odoo.exceptions import ValidationError, UserError

try:
    commitment = self._create_budget_commitment(
        amount=self.amount_total,
        activity_analytic_id=activity,
        fund_analytic_id=fund
    )
except ValidationError as e:
    # Missing required fields or invalid data
    _logger.error(f"Validation error: {e}")
    raise
except UserError as e:
    # Insufficient budget or business logic error
    _logger.warning(f"Business error: {e}")
    raise
```

## Best Practices

1. **Separate Budget Reservation from Document Confirmation**
   ```python
   def action_reserve_budget(self):
       """Reserve budget before document confirmation"""
       result = self._check_budget_availability(
           amount=self.amount,
           activity_analytic_id=self.activity_id,
           fund_analytic_id=self.fund_id
       )
       if result['is_sufficient']:
           commitment = self._create_budget_commitment(
               amount=self.amount,
               activity_analytic_id=self.activity_id,
               fund_analytic_id=self.fund_id
           )
           # Commitment automatically stored in dynamic field
   
   def button_confirm(self):
       """Require budget reservation before confirmation"""
       if (self._get_commitment_field_value('account_id') and 
           not self._get_commitment_field_value('commitment_id')):
           raise UserError(_("Please reserve budget first"))
       return super().button_confirm()
   ```

2. **Handle State Transitions**
   ```python
   # Cancel commitment when document is cancelled - uses dynamic field automatically
   if self.state == 'cancel':
       self._cancel_budget_commitment()
   ```

3. **Track Consumption**
   ```python
   # Consume when payment is made - uses dynamic field automatically
   if payment.state == 'posted':
       self._consume_commitment(
           payment.amount,
           reference=f"Payment: {payment.name}"
       )
   ```

## Troubleshooting

### Common Issues

1. **ValidationError: Budget account field is not set**
   - Solution: Ensure your budget account field is populated and the field name is correctly configured

2. **ValidationError: Activity dimension is required**
   - Solution: Always provide both `activity_analytic_id` and `fund_analytic_id` as they are mandatory

3. **UserError: Insufficient budget**
   - Solution: Use `_check_budget_availability()` before creating commitments

4. **ValidationError: No fiscal year found**
   - Solution: Ensure fiscal year is configured for the commitment date

### Debugging Tips

- Enable debug logging to see commitment creation details
- Access commitment fields directly from the budget.commitment record
- Check budget.controller for available budget calculations
- Verify dynamic field configuration with `_get_commitment_field_value()`