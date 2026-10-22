# 07-purchase-order
> 15+ modules | Purchase order management with budget control, guarantees, and work acceptance

## Module Map

### purchase_kmitl/ (application)
- **Purpose**: Core purchase order customizations for KMITL
- **Depends**: purchase, account_analytic_kmitl, budget
- **Models**:
  - `purchase.order` → Extended with KMITL fields
    - Key fields: budget_commitment_ids, analytic_distribution
    - Key methods: action_create_budget_commitment()
- **Views**: purchase_order_views.xml

### purchase_budget/ (extension)
- **Purpose**: Budget integration for purchase orders
- **Depends**: purchase_kmitl, budget
- **Models**: Budget commitment creation
- **Views**: Budget control views

### purchase_order_kmitl/ (extension)
- **Purpose**: Additional KMITL-specific purchase order features
- **Depends**: purchase_kmitl
- **Models**: Extended fields and methods
- **Views**: Enhanced PO views

### purchase_order_operating_unit/ (extension)
- **Purpose**: Operating unit support for purchase orders
- **Depends**: purchase_kmitl, operating_unit
- **Models**: OU restrictions
- **Views**: OU filters

### purchase_order_change/ (extension)
- **Purpose**: Purchase order change management
- **Depends**: purchase_kmitl
- **Models**:
  - `purchase.order.change` → Change request model
    - States: draft → approved → applied
- **Views**: Change request views

### purchase_order_disbursement/ (extension)
- **Purpose**: Disbursement integration for purchase orders
- **Depends**: purchase_kmitl, disbursement
- **Models**: Payment links
- **Views**: Disbursement views

### purchase_order_expiration/ (extension)
- **Purpose**: Purchase order expiration handling
- **Depends**: purchase_kmitl
- **Models**: Expiration dates and alerts
- **Views**: Expiration warnings

### purchase_contract_kmitl/ (extension)
- **Purpose**: Contract management for purchase orders
- **Depends**: purchase_kmitl, agreement
- **Models**: Contract links
- **Views**: Contract views

### purchase_guarantee_kmitl/ (extension)
- **Purpose**: Guarantee management for purchases
- **Depends**: purchase_kmitl
- **Models**:
  - `purchase.guarantee` → Guarantee tracking
    - States: draft → active → expired
- **Views**: Guarantee views

### purchase_work_acceptance_kmitl/ (extension)
- **Purpose**: Work acceptance for purchase orders
- **Depends**: purchase_kmitl
- **Models**:
  - `purchase.work.acceptance` → Acceptance process
    - States: draft → approved → done
- **Views**: Acceptance views

### purchase_invoice_plan_kmitl/ (extension)
- **Purpose**: Invoice planning for purchase orders
- **Depends**: purchase_kmitl
- **Models**: Invoice schedule planning
- **Views**: Invoice plan views

### purchase_manual_delivery_kmitl/ (extension)
- **Purpose**: Manual delivery management
- **Depends**: purchase_kmitl, stock
- **Models**: Delivery overrides
- **Views**: Delivery views

### purchase_approval_tier_validaiton/ (extension)
- **Purpose**: Tier validation for purchase approvals
- **Depends**: purchase_kmitl, base_tier_validation
- **Models**: Approval workflow
- **Views**: Approval views

### purchase_sequence_kmitl/ (extension)
- **Purpose**: Custom sequencing for purchase orders
- **Depends**: purchase_kmitl
- **Models**: Sequence rules
- **Views**: None

### purchase_order_state_kmitl/ (extension)
- **Purpose**: Custom states for purchase orders
- **Depends**: purchase_kmitl
- **Models**: Additional states
- **Views**: State workflow views
