# 16-approval-sarabun
> 4 modules | Approval workflows and Sarabun font support

## Module Map

### agx_approval/ (application)
- **Purpose**: Advanced approval workflow system
- **Depends**: mail, base_tier_validation
- **Models**:
  - `agx.approval` → Approval request model
    - States: draft → pending → approved → rejected
    - Key fields: name, approver_ids, approval_type
    - Key methods: action_submit(), action_approve(), action_reject()
- **Views**: approval_views.xml

### agx_approval_disbursement/ (extension)
- **Purpose**: Disbursement approval integration
- **Depends**: agx_approval, disbursement
- **Models**: Disbursement approval workflow
- **Views**: Disbursement approval views

### agx_sarabun/ (extension)
- **Purpose**: Sarabun Thai font support
- **Depends**: web
- **Models**: None
- **Views**: Font integration

### office_order/ (extension)
- **Purpose**: Office order management
- **Depends**: agx_approval, agx_sarabun
- **Models**:
  - `office.order` → Office order model
    - States: draft → approved → issued
- **Views**: Office order views
