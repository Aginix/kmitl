# 09-disbursement
> 3 modules | Disbursement management and approval system

## Module Map

### disbursement/ (application)
- **Purpose**: Core disbursement management system
- **Depends**: account, account_analytic_kmitl, budget, purchase_kmitl
- **Models**:
  - `disbursement` → Main disbursement model
    - States: draft → submit → approve → paid → cancel
    - Key fields: name, amount, vendor_id, purchase_order_id, analytic_distribution
    - Key methods: action_submit(), action_approve(), action_pay()
- **Views**: disbursement_views.xml

### disbursement_sarabun/ (extension)
- **Purpose**: Sarabun font support for disbursement reports
- **Depends**: disbursement, agx_sarabun
- **Models**: None
- **Views**: Report templates with Sarabun

### agx_approval_disbursement/ (extension)
- **Purpose**: Advanced approval workflow for disbursements
- **Depends**: disbursement, agx_approval
- **Models**: Approval integration
- **Views**: Approval workflow views
