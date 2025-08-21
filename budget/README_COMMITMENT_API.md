# Budget Commitment API Documentation

## Overview

The `budget.commitment.mixin` provides a flexible API interface for other Odoo modules to integrate with the budget commitment system. This mixin allows any model to create, validate, and manage budget commitments using either record-based or parameter-based approaches.

## Integration Approaches

### Approach 1: Record-based (with analytic.distribution.mixin)
✅ **Recommended** for models that need analytic fields in UI
- Inherit both `analytic.distribution.mixin` and `budget.commitment.mixin`
- Use `_create_budget_commitment_from_record()` method
- Automatic analytic field detection from record

### Approach 2: Parameter-based (flexible)
✅ **Recommended** for simple integrations or custom analytic structures
- Inherit only `budget.commitment.mixin`
- Use `_create_budget_commitment()` method with explicit parameters
- Full control over analytic dimensions

### Approach 3: Hybrid
✅ **Advanced** usage with conditional overrides
- Combine record fields with parameter overrides
- Use `_create_budget_commitment_from_record()` with parameter overrides

## Features

- ✅ **Flexible Integration** - Works with or without analytic.distribution.mixin
- ✅ **Multiple API Methods** - Record-based and parameter-based approaches
- ✅ **Automatic Validation** - Built-in validation and error handling
- ✅ **Budget Availability Checking** - Real-time budget availability verification
- ✅ **4D Analytic Dimensions** - Full support for KMITL's 4-dimensional financial framework
- ✅ **Lifecycle Management** - Complete commitment state management
- ✅ **Consumption Tracking** - Track and consume committed amounts
- ✅ **Backward Compatibility** - Legacy methods still supported

## Installation

The mixin is automatically available when the `budget` module is installed. No additional installation is required.

## Basic Usage

### Option 1: Record-based Integration (with analytic.distribution.mixin)

```python
class YourModelWithAnalytics(models.Model):
    _name = 'your.model'
    _inherit = ['your.model', 'analytic.distribution.mixin', 'budget.commitment.mixin']
    
    budget_account_id = fields.Many2one('budget.account')
    budget_commitment_id = fields.Many2one('budget.commitment')
    
    # Analytic fields automatically provided by analytic.distribution.mixin:
    # - activity_analytic_id, department_analytic_id, fund_analytic_id, source_analytic_id
```

### Option 2: Parameter-based Integration (flexible)

```python
class YourModelFlexible(models.Model):
    _name = 'your.model'
    _inherit = ['your.model', 'budget.commitment.mixin']  # Only this mixin!
    
    budget_account_id = fields.Many2one('budget.account')
    budget_commitment_id = fields.Many2one('budget.commitment')
    
    # Your own analytic fields (any names)
    project_id = fields.Many2one('account.analytic.account')
    funding_id = fields.Many2one('account.analytic.account')
```

### Usage Examples

#### Option 1: Using Record's Analytic Fields
```python
def action_confirm(self):
    # Uses analytic fields from the record automatically
    commitment = self._create_budget_commitment_from_record(
        amount=self.amount_total,
        budget_account_id=self.budget_account_id,
        ref=self.name,
        auto_reserve=True
    )
    self.budget_commitment_id = commitment
```

#### Option 2: Using Manual Parameters
```python
def action_confirm(self):
    # Specify analytic dimensions explicitly
    commitment = self._create_budget_commitment(
        amount=self.amount_total,
        budget_account_id=self.budget_account_id,
        activity_analytic_id=self.project_id,
        fund_analytic_id=self.funding_id,
        ref=self.name,
        auto_reserve=True
    )
    self.budget_commitment_id = commitment
```

## API Methods

### Core Methods

#### `_create_budget_commitment_from_record(amount, budget_account_id, **kwargs)`

Creates a budget commitment using the record's analytic dimension fields.

**Parameters:**
- `amount` (float): Amount to commit
- `budget_account_id`: Budget account (record or ID)
- `ref` (str, optional): Reference document number
- `description` (str, optional): Commitment description
- `date` (date, optional): Commitment date (default: today)
- `auto_reserve` (bool): Automatically reserve the commitment (default: True)
- `**kwargs`: Additional optional fields

**Returns:** `budget.commitment` record

**Note:** The method automatically uses the record's analytic dimension fields or falls back to kwargs parameters.

**Example:**
```python
# Uses record's analytic fields if available
commitment = self._create_budget_commitment_from_record(
    amount=5000.00,
    budget_account_id=self.budget_account_id,
    ref=f"PO/{self.name}",
    auto_reserve=True
)
```

#### `_create_budget_commitment(amount, budget_account_id, activity_analytic_id, fund_analytic_id, **kwargs)`

Creates a budget commitment with explicit analytic parameters.

**Parameters:**
- `amount` (float): Amount to commit
- `budget_account_id`: Budget account (record or ID)
- `activity_analytic_id`: Activity dimension (record or ID) - Required
- `fund_analytic_id`: Fund dimension (record or ID) - Required
- `department_analytic_id`: Department dimension (record or ID) - Optional
- `source_analytic_id`: Source dimension (record or ID) - Optional
- `ref` (str, optional): Reference document number
- `description` (str, optional): Commitment description
- `auto_reserve` (bool): Automatically reserve the commitment (default: True)
- `**kwargs`: Additional optional fields

**Returns:** `budget.commitment` record

**Example:**
```python
# Specify analytic dimensions explicitly
commitment = self._create_budget_commitment(
    amount=5000.00,
    budget_account_id=budget_account,
    activity_analytic_id=activity_record,
    fund_analytic_id=fund_record,
    department_analytic_id=department_record,
    ref=f"PO/{self.name}",
    auto_reserve=True
)
```

#### `_check_budget_availability_from_record(amount, budget_account_id, **kwargs)`

Checks budget availability using the record's analytic dimensions.

**Parameters:**
- `amount` (float): Amount to check
- `budget_account_id`: Budget account (record or ID)
- `**kwargs`: Optional overrides for date_range_fy_id, company_id

**Note:** Uses the record's analytic dimension fields or falls back to kwargs parameters.

**Example:**
```python
result = self._check_budget_availability_from_record(
    amount=self.total_amount,
    budget_account_id=self.budget_account_id
)

if not result['is_sufficient']:
    raise UserError(f"Insufficient budget: {result['message']}")
```

#### `_check_budget_availability(amount, budget_account_id, activity_analytic_id, fund_analytic_id, **kwargs)`

Checks budget availability with explicit analytic parameters.

**Parameters:**
- `amount` (float): Amount to check
- `budget_account_id`: Budget account (record or ID)
- `activity_analytic_id`: Activity dimension (record or ID) - Required
- `fund_analytic_id`: Fund dimension (record or ID) - Required
- `department_analytic_id`: Department dimension (record or ID) - Optional
- `source_analytic_id`: Source dimension (record or ID) - Optional
- `**kwargs`: Additional optional fields

**Returns:** Dictionary with budget availability information

**Example:**
```python
result = self._check_budget_availability(
    amount=self.total_amount,
    budget_account_id=self.budget_account_id,
    activity_analytic_id=self.project_activity,
    fund_analytic_id=self.funding_source
)

if not result['is_sufficient']:
    raise UserError(f"Insufficient budget: {result['message']}")
```

#### `_check_budget_availability(values)` [DEPRECATED]

Legacy method for backward compatibility. Use `_check_budget_availability_from_record` instead.

**Parameters:**
- `values` (dict): Same as `_create_budget_commitment`

**Returns:** Dictionary with:
- `available` (float): Available budget amount
- `requested` (float): Requested amount
- `is_sufficient` (bool): True if budget is sufficient
- `status` (str): 'sufficient', 'warning', or 'insufficient'
- `message` (str): Human-readable status message
- `percentage` (float): Percentage of available budget requested

**Example:**
```python
# Legacy method - for backward compatibility only
result = self._check_budget_availability({
    'amount': self.total_amount,
    'account_id': self.budget_account_id.id,
    'activity_analytic_id': self.activity_id.id,
    'fund_analytic_id': self.fund_id.id,
})

if not result['is_sufficient']:
    raise UserError(f"Insufficient budget: {result['message']}")
```

#### `_consume_commitment_from_record(commitment, amount, reference=None)`

Records consumption against a commitment using the record's analytics.

**Parameters:**
- `commitment`: Budget commitment record
- `amount` (float): Amount to consume
- `reference` (str, optional): Reference for the consumption

**Returns:** `budget.move` record

**Example:**
```python
# Consume budget when invoice is paid
budget_move = self._consume_commitment_from_record(
    self.budget_commitment_id,
    invoice.amount_total,
    reference=f"Invoice: {invoice.number}"
)
```

### Management Methods

#### `_cancel_budget_commitment(commitment)`

Cancels a commitment and releases the reserved budget.

**Parameters:**
- `commitment`: Budget commitment record to cancel

**Returns:** Boolean (True if successful)

**Example:**
```python
if self.state == 'cancel' and self.budget_commitment_id:
    self._cancel_budget_commitment(self.budget_commitment_id)
```

#### `_close_budget_commitment(commitment)`

Marks a commitment as done, releasing any unused budget.

**Parameters:**
- `commitment`: Budget commitment record to close

**Returns:** Boolean (True if successful)

#### `_update_commitment_amount(commitment, new_amount)`

Updates the commitment amount with validation.

**Parameters:**
- `commitment`: Budget commitment record
- `new_amount` (float): New commitment amount

**Returns:** Boolean (True if successful)

**Example:**
```python
# Update commitment when order amount changes
if self.budget_commitment_id and self.state == 'confirmed':
    self._update_commitment_amount(
        self.budget_commitment_id,
        self.new_total_amount
    )
```

#### `_get_commitment_info(commitment)`

Gets detailed information about a commitment.

**Parameters:**
- `commitment`: Budget commitment record

**Returns:** Dictionary with commitment details

## Complete Integration Examples

### Approach 1: Purchase Order with Record-based Analytics

```python
class PurchaseOrderWithAnalytics(models.Model):
    _inherit = ['purchase.order', 'analytic.distribution.mixin', 'budget.commitment.mixin']
    
    budget_commitment_id = fields.Many2one('budget.commitment')
    budget_account_id = fields.Many2one('budget.account')
    
    def button_confirm(self):
        """Create budget commitment using record's analytic fields"""
        for order in self:
            if order.budget_account_id and not order.budget_commitment_id:
                # Simple - uses record's analytic fields automatically
                commitment = order._create_budget_commitment_from_record(
                    amount=order.amount_total,
                    budget_account_id=order.budget_account_id,
                    ref=order.name,
                    auto_reserve=True
                )
                order.budget_commitment_id = commitment
        return super().button_confirm()
```

### Approach 2: Purchase Order with Parameter-based Analytics

```python
class PurchaseOrderFlexible(models.Model):
    _inherit = ['purchase.order', 'budget.commitment.mixin']  # Only this mixin!
    
    budget_commitment_id = fields.Many2one('budget.commitment')
    budget_account_id = fields.Many2one('budget.account')
    
    # Custom analytic fields
    project_activity_id = fields.Many2one('account.analytic.account')
    funding_source_id = fields.Many2one('account.analytic.account')
    department_id = fields.Many2one('account.analytic.account')
    
    def button_confirm(self):
        """Create budget commitment using explicit parameters"""
        for order in self:
            if order.budget_account_id and not order.budget_commitment_id:
                # Explicit analytic parameters
                commitment = order._create_budget_commitment(
                    amount=order.amount_total,
                    budget_account_id=order.budget_account_id,
                    activity_analytic_id=order.project_activity_id,
                    fund_analytic_id=order.funding_source_id,
                    department_analytic_id=order.department_id,
                    ref=order.name,
                    auto_reserve=True
                )
                order.budget_commitment_id = commitment
        return super().button_confirm()
```

### Approach 3: Invoice with Manual Analytics (No Analytic Mixin)

```python
class AccountMoveSimple(models.Model):
    _inherit = ['account.move', 'budget.commitment.mixin']  # Only budget mixin!
    
    budget_commitment_id = fields.Many2one('budget.commitment')
    
    def action_post(self):
        """Create budget commitment for vendor bills"""
        if self.move_type == 'in_invoice':
            # Get analytic info from somewhere else (configuration, lines, etc.)
            activity = self._get_activity_from_lines()
            fund = self._get_fund_from_configuration()
            
            if activity and fund:
                commitment = self._create_budget_commitment(
                    amount=self.amount_total,
                    budget_account_id=self._get_budget_account(),
                    activity_analytic_id=activity,
                    fund_analytic_id=fund,
                    ref=self.name,
                    auto_reserve=True
                )
                self.budget_commitment_id = commitment
        
        return super().action_post()
    
    def _get_activity_from_lines(self):
        """Get activity from invoice lines or other logic"""
        # Custom logic to determine activity
        return self.line_ids[0].analytic_account_id  # example
```

## Error Handling

The mixin provides comprehensive error handling:

```python
from odoo.exceptions import ValidationError, UserError

try:
    # Option 1: Record-based
    commitment = self._create_budget_commitment_from_record(
        amount=self.amount_total,
        budget_account_id=self.budget_account_id
    )
    
    # Option 2: Parameter-based
    commitment = self._create_budget_commitment(
        amount=self.amount_total,
        budget_account_id=self.budget_account_id,
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

1. **Always Check Before Committing**
   ```python
   # Check first using record's analytic fields
   result = self._check_budget_availability_from_record(
       amount=self.amount,
       budget_account_id=self.budget_account_id
   )
   if result['is_sufficient']:
       commitment = self._create_budget_commitment_from_record(
           amount=self.amount,
           budget_account_id=self.budget_account_id
       )
   ```

2. **Handle State Transitions**
   ```python
   # Cancel commitment when document is cancelled
   if self.state == 'cancel' and self.budget_commitment_id:
       self._cancel_budget_commitment(self.budget_commitment_id)
   ```

3. **Track Consumption**
   ```python
   # Consume when payment is made
   if payment.state == 'posted':
       self._consume_commitment(
           commitment,
           payment.amount,
           reference=f"Payment: {payment.name}"
       )
   ```

4. **Provide User Feedback**
   ```python
   # Show budget status to users
   result = self._check_budget_availability(values)
   return {
       'type': 'ir.actions.client',
       'tag': 'display_notification',
       'params': {
           'title': 'Budget Check',
           'message': result['message'],
           'type': 'success' if result['is_sufficient'] else 'warning',
       }
   }
   ```

## Configuration

### System Parameters

- `budget.allow_negative`: Allow negative budget balances (default: False)

### Required Modules

- `budget`: Core budget module
- `account_analytic_kmitl`: 4D analytic dimensions

## Troubleshooting

### Common Issues

1. **ValidationError: Activity dimension is required**
   - **Record-based approach**: Ensure `activity_analytic_id` field is set on the record
   - **Parameter-based approach**: Pass `activity_analytic_id` parameter to the method
   - Activity dimension is always required for budget commitments

2. **ValidationError: Fund dimension is required**
   - **Record-based approach**: Ensure `fund_analytic_id` field is set on the record
   - **Parameter-based approach**: Pass `fund_analytic_id` parameter to the method
   - Fund dimension is always required for budget commitments

3. **ValidationError: Budget account is required**
   - Ensure `budget_account_id` is provided (either as field or parameter)
   - Check that the budget account exists and is budgetable

4. **UserError: Insufficient budget**
   - Check budget availability before creating commitment
   - Consider using warning instead of blocking if appropriate
   - Verify analytic dimensions are correct

5. **No fiscal year found**
   - Ensure fiscal years are configured for all dates
   - Provide date_range_fy_id explicitly if needed

6. **Method doesn't exist or wrong parameters**
   - **For record-based**: Use `_create_budget_commitment_from_record()` and `_check_budget_availability_from_record()`
   - **For parameter-based**: Use `_create_budget_commitment()` and `_check_budget_availability()`
   - Check method signatures match your usage

## Support

For questions or issues with the Budget Commitment API, please contact the development team or refer to the main budget module documentation.