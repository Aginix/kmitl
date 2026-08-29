# 02-budget-appropriation
> 11 modules | Budget appropriation management with draft planning, approval workflows, and reporting

## Module Map

### budget_appropriation/ (application)
- **Purpose**: Core budget appropriation system with draft planning, review, and posting to budget moves
- **Depends**: budget, account_analytic_kmitl, mail, hr, portal
- **Models**:
  - `budget.appropriation` → `models/budget_appropriation.py`
    - States: draft → review → posted → cancel
    - Key fields: name, ref, date, account_fiscal_year_id, department_analytic_id, source_analytic_id, line_ids, deduct_line_ids, appropriation_type, amount_total
    - Key methods: action_review(), action_post(), action_open_f5_preview(), action_open_f4_preview()
  - `budget.appropriation.line` → `models/budget_appropriation_line.py`
    - Key fields: appropriation_id, budget_account_id, analytic_distribution, amount
- **Views**: budget_appropriation_views.xml, budget_account_views.xml, budget_move_views.xml

### budget_appropriation_demo/ (extension)
- **Purpose**: Demo data for budget appropriation module
- **Depends**: budget_appropriation
- **Models**: None (data only)
- **Views**: None

### budget_appropriation_operating_unit/ (extension)
- **Purpose**: Operating unit support for budget appropriations
- **Depends**: budget_appropriation, operating_unit
- **Models**: Adds operating_unit_id to budget.appropriation
- **Views**: Operating unit filters

### budget_appropriation_operating_unit_access_all/ (extension)
- **Purpose**: Cross-operating unit access for budget appropriations
- **Depends**: budget_appropriation_operating_unit
- **Models**: Access control rules
- **Views**: None

### budget_appropriation_report/ (extension)
- **Purpose**: Enhanced reporting for budget appropriations
- **Depends**: budget_appropriation
- **Models**: Report models
- **Views**: Report views

### budget_appropriation_summary/ (application)
- **Purpose**: Budget appropriation summary and consolidation
- **Depends**: budget_appropriation
- **Models**:
  - `budget.appropriation.summary` → Summary aggregation model
    - Key fields: fiscal_year_id, department_analytic_id, total_amount
- **Views**: Summary views

### budget_appropriation_summary_demo/ (extension)
- **Purpose**: Demo data for budget appropriation summaries
- **Depends**: budget_appropriation_summary
- **Models**: None (data only)
- **Views**: None

### budget_appropriation_summary_f3/ (extension)
- **Purpose**: F3 form reporting for budget appropriation summaries
- **Depends**: budget_appropriation_summary
- **Models**: F3 report model
- **Views**: F3 report views

### budget_appropriation_summary_operating_unit/ (extension)
- **Purpose**: Operating unit support for appropriation summaries
- **Depends**: budget_appropriation_summary, operating_unit
- **Models**: Adds operating_unit_id to summaries
- **Views**: OU summary views

### budget_appropriation_summary_operating_unit_access_all/ (extension)
- **Purpose**: Cross-OU access for appropriation summaries
- **Depends**: budget_appropriation_summary_operating_unit
- **Models**: Access rules
- **Views**: None

### budget_appropriation_tracking/ (extension)
- **Purpose**: Audit trail and tracking for budget appropriation changes
- **Depends**: budget_appropriation
- **Models**: Tracking fields and history
- **Views**: Tracking views
