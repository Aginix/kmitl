# 06-purchase-request
> 23 modules | Purchase request management system with approval workflows, budget integration, and operating unit support

## Module Map

### purchase_request_kmitl/ (application)
- **Purpose**: Core purchase request functionality with procurement types, committees, and Thai government compliance
- **Depends**: hr, purchase_exception, purchase_request_exception, purchase_request_operating_unit, account_fiscal_year, purchase_order_kmitl, purchase_operating_unit, web_m2x_options
- **Models**:
  - `purchase.request` → `models/purchase_request.py`
    - States: draft → to_approve → approved → rejected → in_progress → done
    - Key fields: procurement_type_id, purchase_type_id, procurement_method_id, procurement_committee_ids, work_acceptance_committee_ids, payment_type, account_fiscal_year_id
    - Key methods: button_approved(), get_estimated_cost_currency(), _onchange_purchase_type_id()
  - `purchase.request.line` → `models/purchase_request_line.py`
    - Key fields: product_id, product_qty, estimated_cost, analytic_distribution
  - `procurement.type` → `models/procurement_type.py`
    - Key fields: name, code, description
  - `procurement.method` → `models/procurement_method.py`
    - Key fields: name, code, description
  - `procurement.committee` → `models/procurement_committee.py`
    - Key fields: request_id, partner_id, committee_type, role
- **Views**: purchase_request_views.xml, procurement_method_views.xml, procurement_type_views.xml, procurement_committee_views.xml

### purchase_request_approval_kmitl/ (extension)
- **Purpose**: Advanced approval workflow for purchase requests with tier validation
- **Depends**: purchase_request_kmitl, base_tier_validation
- **Models**: Extends purchase.request with approval states
- **Views**: Custom approval views

### purchase_request_budget/ (extension)
- **Purpose**: Budget integration for purchase requests with commitment tracking
- **Depends**: purchase_request_kmitl, budget
- **Models**: Adds budget fields to purchase.request
- **Views**: Budget-related views

### purchase_request_operating_unit/ (extension)
- **Purpose**: Operating unit support for purchase requests
- **Depends**: purchase_request, operating_unit
- **Models**: Adds operating_unit_id to purchase.request
- **Views**: Operating unit filters

### purchase_request_sarabun/ (extension)
- **Purpose**: Sarabun font support for purchase request reports
- **Depends**: purchase_request_kmitl, agx_sarabun
- **Models**: None
- **Views**: Report templates with Sarabun font

### purchase_request_ux_kmitl/ (extension)
- **Purpose**: UX improvements for purchase request interface
- **Depends**: purchase_request_kmitl
- **Models**: None
- **Views**: Enhanced form views and widgets

### purchase_request_payment_type/ (extension)
- **Purpose**: Payment type classification for purchase requests
- **Depends**: purchase_request_kmitl
- **Models**: Adds payment_type field
- **Views**: Payment type selection

### purchase_request_sequence_kmitl/ (extension)
- **Purpose**: Custom sequence numbering for purchase requests
- **Depends**: purchase_request_kmitl
- **Models**: None
- **Views**: None

### purchase_request_substate/ (extension)
- **Purpose**: Sub-state management for detailed workflow tracking
- **Depends**: purchase_request_kmitl
- **Models**: Adds sub_state field
- **Views**: Sub-state workflow views

### purchase_request_verify_state/ (extension)
- **Purpose**: Verification state in purchase request workflow
- **Depends**: purchase_request_kmitl
- **Models**: Adds verified_by, date_verified fields
- **Views**: Verification workflow

### purchase_request_approval_disbursement/ (extension)
- **Purpose**: Integration with disbursement approval workflow
- **Depends**: purchase_request_approval_kmitl, disbursement
- **Models**: Links purchase requests to disbursements
- **Views**: Disbursement approval views

### purchase_request_approval_work_acceptance/ (extension)
- **Purpose**: Work acceptance approval integration
- **Depends**: purchase_request_approval_kmitl, purchase_work_acceptance_kmitl
- **Models**: Links to work acceptance approvals
- **Views**: Work acceptance views

### purchase_request_to_requisition/ (extension)
- **Purpose**: Convert purchase requests to requisitions
- **Depends**: purchase_request_kmitl, hr_expense
- **Models**: Conversion wizard
- **Views**: Conversion wizard views

### purchase_request_vendor_kmitl/ (extension)
- **Purpose**: Vendor management enhancements for purchase requests
- **Depends**: purchase_request_kmitl
- **Models**: Vendor selection improvements
- **Views**: Vendor selection views

### purchase_request_tender_kmitl/ (extension)
- **Purpose**: Tender process integration for purchase requests
- **Depends**: purchase_request_kmitl
- **Models**: Tender-related fields
- **Views**: Tender management views

### purchase_request_egp/ (extension)
- **Purpose**: E-GP (Electronic Government Procurement) integration
- **Depends**: purchase_request_kmitl
- **Models**: E-GP compliance fields
- **Views**: E-GP interface

### purchase_request_price_tax_included/ (extension)
- **Purpose**: Price tax included calculations
- **Depends**: purchase_request_kmitl
- **Models**: Tax-inclusive pricing
- **Views**: Price calculation views

### purchase_request_department_operating_unit/ (extension)
- **Purpose**: Department-based operating unit restrictions
- **Depends**: purchase_request_operating_unit, hr_department_operating_unit
- **Models**: Department OU validation
- **Views**: Department filters

### purchase_request_budget_procurement/ (extension)
- **Purpose**: Procurement budget integration
- **Depends**: purchase_request_budget, procurement_plan_budget
- **Models**: Procurement budget fields
- **Views**: Budget procurement views

### purchase_request_approval_attach_existing_attachments/ (extension)
- **Purpose**: Attach existing documents to approval workflow
- **Depends**: purchase_request_approval_kmitl
- **Models**: Attachment linking
- **Views**: Attachment selection

### purchase_request_approval_account/ (extension)
- **Purpose**: Accounting integration for purchase request approvals
- **Depends**: purchase_request_approval_kmitl, account
- **Models**: Accounting fields
- **Views**: Accounting views

### purchase_request_operating_unit_access_all/ (extension)
- **Purpose**: Cross-operating unit access for purchase requests
- **Depends**: purchase_request_operating_unit
- **Models**: Access control rules
- **Views**: None

### purchase_request_approval_disbursement_budget/ (extension)
- **Purpose**: Budget validation for disbursement approvals
- **Depends**: purchase_request_approval_disbursement, budget
- **Models**: Budget validation
- **Views**: Budget approval views

### purchase_request_approval_operating_unit/ (extension)
- **Purpose**: Operating unit approval workflows
- **Depends**: purchase_request_approval_kmitl, operating_unit
- **Models**: OU-specific approvals
- **Views**: OU approval views
