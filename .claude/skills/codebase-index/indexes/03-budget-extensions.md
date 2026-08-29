# 03-budget-extensions
> 6 modules | Budget reporting, operating unit integration, and extended budget functionality

## Module Map

### budget_report/ (extension)
- **Purpose**: Comprehensive budget reporting and analytics
- **Depends**: budget
- **Models**: Report models for budget analysis
- **Views**: Budget report dashboards and views

### budget_operating_unit/ (extension)
- **Purpose**: Operating unit restrictions for budget management
- **Depends**: budget, operating_unit
- **Models**: Adds operating_unit_id to budget models
- **Views**: OU-specific budget views

### budget_operating_unit_access_all/ (extension)
- **Purpose**: Cross-operating unit access for budget data
- **Depends**: budget_operating_unit
- **Models**: Access control overrides
- **Views**: None

### budget_project/ (extension)
- **Purpose**: Project-based budget tracking and allocation
- **Depends**: budget, project
- **Models**: Links budget to projects
- **Views**: Project budget views

### budget_product/ (extension)
- **Purpose**: Product-specific budget categorization
- **Depends**: budget, product
- **Models**: Product budget fields
- **Views**: Product budget views

### budget_analytic_account/ (extension)
- **Purpose**: Enhanced analytic account integration for budgets
- **Depends**: budget, account_analytic_kmitl
- **Models**: Analytic distribution in budgets
- **Views**: Analytic budget views
