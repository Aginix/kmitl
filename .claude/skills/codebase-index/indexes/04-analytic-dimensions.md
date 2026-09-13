# 04-analytic-dimensions
> 7 modules | Analytic accounting dimensions and operating unit integration

## Module Map

### account_analytic_kmitl/ (application)
- **Purpose**: KMITL-specific analytic accounting with multi-dimensional structure (activities, departments, funds, sources)
- **Depends**: account_analytic_parent, account_analytic_plan_code, account_analytic_seq
- **Models**:
  - `account.analytic.account` → `models/account_analytic_account.py`
    - Key fields: department_analytic_ids, fund_analytic_ids
  - `analytic.distribution.mixin` → `models/analytic_mixin.py`
    - Key fields: activity_analytic_id, department_analytic_id, fund_analytic_id, source_analytic_id, analytic_distribution
    - Key methods: _compute_analytic_distribution(), _process_analytic_distribution(), _analytic_fields()
- **Views**: account_analytic_account_views.xml

### account_analytic_plan_code/ (extension)
- **Purpose**: Adds code field to analytic plans for better organization
- **Depends**: analytic
- **Models**: None (extends account.analytic.plan)
- **Views**: account_analytic_plan_views.xml

### account_analytic_seq/ (extension)
- **Purpose**: Adds sequence field to analytic accounts for custom ordering
- **Depends**: analytic
- **Models**: None (extends account.analytic.account)
- **Views**: account_analytic_views.xml

### account_analytic_ux_kmitl/ (extension)
- **Purpose**: UX improvements for analytic account management
- **Depends**: account
- **Models**: None
- **Views**: account_analytic_account_views.xml

### analytic_operating_unit_access_all/ (extension)
- **Purpose**: Allows access to analytics across all operating units
- **Depends**: analytic_operating_unit
- **Models**: None
- **Views**: None

### analytic_operating_unit_tree/ (extension)
- **Purpose**: Tree view enhancements for analytic accounts with operating unit context
- **Depends**: analytic_operating_unit
- **Models**: None
- **Views**: account_analytic_account_views.xml

### account_analytic_public/ (extension)
- **Purpose**: Makes analytic accounts publicly accessible
- **Depends**: analytic
- **Models**: None
- **Views**: None
