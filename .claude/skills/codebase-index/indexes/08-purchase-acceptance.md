# 08-purchase-acceptance
> 12+ modules | Purchase acceptance, guarantees, and invoice planning system

## Module Map

### purchase_work_acceptance_kmitl/ (application)
- **Purpose**: Work acceptance process for purchase orders
- **Depends**: purchase_kmitl, account_analytic_kmitl
- **Models**:
  - `purchase.work.acceptance` → Main acceptance model
    - States: draft → approved → done → cancel
    - Key fields: purchase_order_id, acceptance_lines, committee_ids
    - Key methods: action_approve(), action_done()
  - `purchase.work.acceptance.line` → Acceptance line items
    - Key fields: acceptance_id, product_id, accepted_qty, notes
- **Views**: work_acceptance_views.xml

### purchase_guarantee_kmitl/ (application)
- **Purpose**: Guarantee management for purchases
- **Depends**: purchase_kmitl
- **Models**:
  - `purchase.guarantee` → Guarantee tracking
    - States: draft → active → expired → cancelled
    - Key fields: purchase_order_id, guarantee_type, amount, expiry_date
    - Key methods: action_activate(), action_expire()
- **Views**: guarantee_views.xml

### purchase_invoice_plan_kmitl/ (application)
- **Purpose**: Invoice planning and scheduling
- **Depends**: purchase_kmitl, account
- **Models**:
  - `purchase.invoice.plan` → Invoice schedule
    - Key fields: purchase_order_id, installment_date, amount, invoice_id
    - Key methods: action_create_invoice()
- **Views**: invoice_plan_views.xml

### purchase_work_acceptance_disbursement/ (extension)
- **Purpose**: Disbursement integration with work acceptance
- **Depends**: purchase_work_acceptance_kmitl, disbursement
- **Models**: Payment release on acceptance
- **Views**: Disbursement acceptance views

### purchase_work_acceptance_invoice_plan/ (extension)
- **Purpose**: Invoice plan integration with work acceptance
- **Depends**: purchase_work_acceptance_kmitl, purchase_invoice_plan_kmitl
- **Models**: Acceptance-based invoicing
- **Views**: Combined views

### purchase_work_acceptance_portal/ (extension)
- **Purpose**: Portal access for work acceptance
- **Depends**: purchase_work_acceptance_kmitl, portal
- **Models**: Portal security
- **Views**: Portal templates

### purchase_work_acceptance_tier_validation/ (extension)
- **Purpose**: Tier validation for work acceptance approvals
- **Depends**: purchase_work_acceptance_kmitl, base_tier_validation
- **Models**: Approval workflow
- **Views**: Validation views

### purchase_guarantee_account_payment/ (extension)
- **Purpose**: Account payment integration for guarantees
- **Depends**: purchase_guarantee_kmitl, account_payment
- **Models**: Payment links
- **Views**: Payment guarantee views

### purchase_guarantee_bid_guarantee_kmitl/ (extension)
- **Purpose**: Bid guarantee management
- **Depends**: purchase_guarantee_kmitl
- **Models**: Bid-specific guarantees
- **Views**: Bid guarantee views

### purchase_guarantee_expiration/ (extension)
- **Purpose**: Guarantee expiration handling
- **Depends**: purchase_guarantee_kmitl
- **Models**: Expiration alerts
- **Views**: Expiration views

### purchase_guarantee_operating_unit/ (extension)
- **Purpose**: Operating unit support for guarantees
- **Depends**: purchase_guarantee_kmitl, operating_unit
- **Models**: OU restrictions
- **Views**: OU guarantee views

### purchase_invoice_plan_account_move_request/ (extension)
- **Purpose**: Account move request integration
- **Depends**: purchase_invoice_plan_kmitl, account_move_request
- **Models**: Move request creation
- **Views**: Move request views

### purchase_invoice_plan_deliverables/ (extension)
- **Purpose**: Deliverables tracking in invoice plans
- **Depends**: purchase_invoice_plan_kmitl
- **Models**: Deliverable milestones
- **Views**: Deliverable views

### purchase_invoice_plan_usability/ (extension)
- **Purpose**: Usability improvements for invoice planning
- **Depends**: purchase_invoice_plan_kmitl
- **Models**: UX enhancements
- **Views**: Enhanced forms
