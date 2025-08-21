# Budget Commitment API Documentation

This document describes the Budget Commitment Mixin API, a standardized interface that allows any Odoo module to integrate with the budget commitment system without direct dependencies.

## Overview

The `budget.commitment.mixin` provides a clean, parameter-based API for:
- Creating budget commitments with proper validation
- Checking budget availability before making commitments
- Managing commitment lifecycle (reserve, consume, cancel, close)
- Tracking budget consumption through invoice and payment workflows

## Integration Methods

The mixin uses a simple parameter-based approach where you explicitly pass analytic dimension IDs to the API methods.

### Basic Usage

```python
class PurchaseOrder(models.Model):
    _inherit = ['purchase.order', 'budget.commitment.mixin']
    
    budget_commitment_id = fields.Many2one('budget.commitment')
    budget_account_id = fields.Many2one('budget.account')
    
    # Custom analytic fields
    project_activity_id = fields.Many2one('account.analytic.account')
    funding_source_id = fields.Many2one('account.analytic.account')
    
    def action_reserve_budget(self):
        commitment = self._create_budget_commitment(
            amount=self.amount_total,
            budget_account_id=self.budget_account_id,
            activity_analytic_id=self.project_activity_id,
            fund_analytic_id=self.funding_source_id
        )
        self.budget_commitment_id = commitment
```

## API Methods

### Creation Methods

#### `_create_budget_commitment(amount, budget_account_id, activity_analytic_id, fund_analytic_id, **kwargs)`

Creates a budget commitment with explicit analytic parameters.

**Parameters:**
- `amount` (float): Amount to commit - Required
- `budget_account_id`: Budget account (record or ID) - Required  
- `activity_analytic_id`: Activity dimension (record or ID) - Required
- `fund_analytic_id`: Fund dimension (record or ID) - Required
- `department_analytic_id`: Department dimension (record or ID) - Optional
- `source_analytic_id`: Source dimension (record or ID) - Optional
- `ref` (str, optional): Reference for the commitment
- `description` (str, optional): Description text
- `auto_reserve` (bool, optional): Automatically reserve the commitment (default: True)
- Additional kwargs: `date`, `user_id`, `company_id`, `date_range_fy_id`

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

### Validation Methods

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

### Consumption Methods

#### `_consume_commitment(commitment, amount, reference=None)`

Consumes budget from a commitment.

**Parameters:**
- `commitment`: Budget commitment record
- `amount` (float): Amount to consume
- `reference` (str, optional): Reference for the consumption

**Returns:** `budget.move` record

**Example:**
```python
# Consume budget when invoice is paid
budget_move = self._consume_commitment(
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

## Complete Integration Example

### Purchase Order with Parameter-based Analytics

```python
class PurchaseOrder(models.Model):
    _inherit = ['purchase.order', 'budget.commitment.mixin']
    
    budget_commitment_id = fields.Many2one('budget.commitment')
    budget_account_id = fields.Many2one('budget.account')
    
    # Custom analytic fields
    project_activity_id = fields.Many2one('account.analytic.account')
    funding_source_id = fields.Many2one('account.analytic.account')
    department_id = fields.Many2one('account.analytic.account')
    
    def action_reserve_budget(self):
        """Reserve budget using explicit parameters"""
        self.ensure_one()
        if self.budget_commitment_id:
            raise UserError(_("Budget already reserved"))
        
        # Explicit analytic parameters
        commitment = self._create_budget_commitment(
            amount=self.amount_total,
            budget_account_id=self.budget_account_id,
            activity_analytic_id=self.project_activity_id,
            fund_analytic_id=self.funding_source_id,
            department_analytic_id=self.department_id,
            ref=self.name,
            auto_reserve=True
        )
        self.budget_commitment_id = commitment
    
    def button_confirm(self):
        """Confirm order - check budget is reserved first"""
        for order in self:
            if order.budget_account_id and not order.budget_commitment_id:
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

1. **Separate Budget Reservation from Document Confirmation**
   ```python
   def action_reserve_budget(self):
       """Reserve budget before document confirmation"""
       result = self._check_budget_availability(
           amount=self.amount,
           budget_account_id=self.budget_account_id,
           activity_analytic_id=self.activity_id,
           fund_analytic_id=self.fund_id
       )
       if result['is_sufficient']:
           commitment = self._create_budget_commitment(
               amount=self.amount,
               budget_account_id=self.budget_account_id,
               activity_analytic_id=self.activity_id,
               fund_analytic_id=self.fund_id
           )
           self.budget_commitment_id = commitment
   
   def button_confirm(self):
       """Require budget reservation before confirmation"""
       if self.budget_account_id and not self.budget_commitment_id:
           raise UserError(_("Please reserve budget first"))
       return super().button_confirm()
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

## Troubleshooting

### Common Issues

1. **ValidationError: Activity dimension is required**
   - Solution: Always provide both `activity_analytic_id` and `fund_analytic_id` as they are mandatory

2. **UserError: Insufficient budget**
   - Solution: Use `_check_budget_availability()` before creating commitments

3. **ValidationError: No fiscal year found**
   - Solution: Ensure fiscal year is configured for the commitment date

### Debugging Tips

- Enable debug logging to see commitment creation details
- Use `_get_commitment_info()` to inspect commitment state
- Check budget.controller for available budget calculations