# Budget Commitment API Documentation

## Overview

The `budget.commitment.mixin` provides a standardized API interface for other Odoo modules to integrate with the budget commitment system. This mixin allows any model to create, validate, and manage budget commitments without directly depending on the budget.commitment model.

## Requirements

⚠️ **Important**: Models using `budget.commitment.mixin` **MUST** also inherit from `analytic.distribution.mixin` to provide the required 4D analytic dimension fields:
- `activity_analytic_id` - Activity/Program dimension
- `department_analytic_id` - Department/Organization dimension
- `fund_analytic_id` - Fund source dimension
- `source_analytic_id` - Money source classification

## Features

- ✅ **Standard API Methods** - Consistent interface for all commitment operations
- ✅ **Automatic Validation** - Built-in validation and error handling
- ✅ **Budget Availability Checking** - Real-time budget availability verification
- ✅ **4D Analytic Dimensions** - Full support for KMITL's 4-dimensional financial framework
- ✅ **Lifecycle Management** - Complete commitment state management
- ✅ **Consumption Tracking** - Track and consume committed amounts

## Installation

The mixin is automatically available when the `budget` module is installed. No additional installation is required.

## Basic Usage

### 1. Inherit Both Required Mixins

```python
class YourModel(models.Model):
    _name = 'your.model'
    # MUST inherit BOTH mixins:
    _inherit = ['your.model', 'analytic.distribution.mixin', 'budget.commitment.mixin']
    
    # Add budget account field (required)
    budget_account_id = fields.Many2one(
        'budget.account',
        string='Budget Account',
        domain=[('budgetable', '=', True)]
    )
    
    # Optional: Add field to store commitment reference
    budget_commitment_id = fields.Many2one(
        'budget.commitment',
        string='Budget Commitment',
        readonly=True
    )
    
    # Note: The 4D analytic dimension fields are automatically provided
    # by analytic.distribution.mixin:
    # - activity_analytic_id
    # - department_analytic_id
    # - fund_analytic_id
    # - source_analytic_id
```

### 2. Create a Budget Commitment

```python
def your_action_method(self):
    # Create budget commitment using record's analytic fields
    commitment = self._create_budget_commitment_from_record(
        amount=10000.00,
        budget_account_id=self.budget_account_id,
        ref=self.name,
        description=f"Document: {self.name}",
        date=fields.Date.today(),
        auto_reserve=True
    )
    
    # Store reference
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

**Note:** The method automatically uses the record's analytic dimension fields (activity_analytic_id, department_analytic_id, fund_analytic_id, source_analytic_id) from the analytic.distribution.mixin.

**Example:**
```python
# The method uses self's analytic fields directly
commitment = self._create_budget_commitment_from_record(
    amount=5000.00,
    budget_account_id=self.budget_account_id,
    ref=f"PO/{self.name}",
    description="Purchase Order for Office Supplies",
    auto_reserve=True
)
```

#### `_check_budget_availability_from_record(amount, budget_account_id, **kwargs)`

Checks budget availability using the record's analytic dimensions.

**Parameters:**
- `amount` (float): Amount to check
- `budget_account_id`: Budget account (record or ID)
- `**kwargs`: Optional overrides for date_range_fy_id, company_id

**Note:** Uses the record's analytic dimension fields automatically.

**Example:**
```python
result = self._check_budget_availability_from_record(
    amount=self.total_amount,
    budget_account_id=self.budget_account_id
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

### Purchase Order Integration

```python
class PurchaseOrder(models.Model):
    # MUST inherit both mixins
    _inherit = ['purchase.order', 'analytic.distribution.mixin', 'budget.commitment.mixin']
    
    budget_commitment_id = fields.Many2one('budget.commitment')
    budget_account_id = fields.Many2one('budget.account')
    # Note: analytic fields are provided by analytic.distribution.mixin
    
    def button_confirm(self):
        """Create budget commitment on PO confirmation"""
        for order in self:
            if order.budget_account_id and not order.budget_commitment_id:
                # Check budget first using record's analytic fields
                check = order._check_budget_availability_from_record(
                    amount=order.amount_total,
                    budget_account_id=order.budget_account_id
                )
                
                if not check['is_sufficient']:
                    raise UserError(f"Insufficient budget: {check['message']}")
                
                # Create commitment using record's analytic fields
                commitment = order._create_budget_commitment_from_record(
                    amount=order.amount_total,
                    budget_account_id=order.budget_account_id,
                    ref=order.name,
                    auto_reserve=True
                )
                
                order.budget_commitment_id = commitment
        
        return super().button_confirm()
    
    def button_cancel(self):
        """Cancel commitment when PO is cancelled"""
        for order in self:
            if order.budget_commitment_id:
                self._cancel_budget_commitment(order.budget_commitment_id)
        return super().button_cancel()
```

### Expense Report Integration

```python
class HrExpenseSheet(models.Model):
    # MUST inherit both mixins
    _inherit = ['hr.expense.sheet', 'analytic.distribution.mixin', 'budget.commitment.mixin']
    
    budget_commitment_id = fields.Many2one('budget.commitment')
    budget_account_id = fields.Many2one('budget.account')
    require_budget = fields.Boolean(default=True)
    
    def action_submit_sheet(self):
        """Check budget before submission"""
        if self.require_budget:
            # Check using sheet's analytic fields
            result = self._check_budget_availability_from_record(
                amount=self.total_amount,
                budget_account_id=self.budget_account_id
            )
            
            if not result['is_sufficient']:
                raise UserError(
                    f"Cannot submit expense: {result['message']}"
                )
        
        return super().action_submit_sheet()
    
    def _do_approve(self):
        """Create commitment on approval"""
        if self.require_budget and not self.budget_commitment_id:
            # Create using sheet's analytic fields
            commitment = self._create_budget_commitment_from_record(
                amount=self.total_amount,
                budget_account_id=self.budget_account_id,
                ref=self.name,
                auto_reserve=True
            )
            self.budget_commitment_id = commitment
        
        return super()._do_approve()
```

## Error Handling

The mixin provides comprehensive error handling:

```python
from odoo.exceptions import ValidationError, UserError

try:
    commitment = self._create_budget_commitment_from_record(
        amount=values['amount'],
        budget_account_id=values['budget_account_id']
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

1. **ValidationError: Model must inherit from 'analytic.distribution.mixin'**
   - Ensure your model inherits from BOTH 'analytic.distribution.mixin' AND 'budget.commitment.mixin'
   - The analytic.distribution.mixin provides the required 4D dimension fields

2. **ValidationError: Missing required field**
   - Ensure all required fields are provided:
     - budget_account_id (must be defined in your model)
     - activity_analytic_id and fund_analytic_id (from analytic.distribution.mixin)
   - Check that analytic dimensions are properly set on the record

3. **UserError: Insufficient budget**
   - Check budget availability before creating commitment
   - Consider using warning instead of blocking if appropriate

4. **No fiscal year found**
   - Ensure fiscal years are configured for all dates
   - Provide date_range_fy_id explicitly if needed

## Support

For questions or issues with the Budget Commitment API, please contact the development team or refer to the main budget module documentation.