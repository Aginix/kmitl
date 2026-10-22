# 13-project
> 3 modules | Project management and construction tracking

## Module Map

### kmitl_project/ (application)
- **Purpose**: KMITL project management system
- **Depends**: project, account_analytic_kmitl, budget
- **Models**:
  - `project.project` → Extended project model
    - Key fields: budget_account_id, analytic_account_id, operating_unit_id
    - Key methods: Project-specific methods
- **Views**: project_views.xml

### kmitl_project_widget_ztree/ (extension)
- **Purpose**: ZTree widget for project hierarchies
- **Depends**: kmitl_project, web
- **Models**: None
- **Views**: Tree widget integration

### agx_construction/ (extension)
- **Purpose**: Construction project management
- **Depends**: kmitl_project, purchase_work_acceptance_kmitl
- **Models**:
  - `construction.project` → Construction-specific features
    - Key fields: contract_value, completion_percentage
- **Views**: Construction views
