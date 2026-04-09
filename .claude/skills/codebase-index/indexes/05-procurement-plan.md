# 05-procurement-plan
> 9 modules | Procurement planning system with budget integration and operating unit support

## Module Map

### procurement_plan/ (application)
- **Purpose**: Core procurement planning with annual planning cycles
- **Depends**: account_fiscal_year, account_analytic_kmitl, budget
- **Models**:
  - `procurement.plan` → Main planning model
    - States: draft → approved → done
    - Key fields: fiscal_year_id, department_analytic_id, line_ids
    - Key methods: action_approve(), action_done()
  - `procurement.plan.line` → Planning line items
    - Key fields: plan_id, product_id, quantity, estimated_cost
- **Views**: procurement_plan_views.xml

### procurement_plan_demo/ (extension)
- **Purpose**: Demo data for procurement planning
- **Depends**: procurement_plan
- **Models**: None (data only)
- **Views**: None

### procurement_plan_budget/ (extension)
- **Purpose**: Budget integration for procurement plans
- **Depends**: procurement_plan, budget
- **Models**: Budget commitment links
- **Views**: Budget planning views

### procurement_plan_operating_unit/ (extension)
- **Purpose**: Operating unit support for procurement plans
- **Depends**: procurement_plan, operating_unit
- **Models**: Adds operating_unit_id
- **Views**: OU filters

### procurement_plan_operating_unit_access_all/ (extension)
- **Purpose**: Cross-OU access for procurement plans
- **Depends**: procurement_plan_operating_unit
- **Models**: Access rules
- **Views**: None

### procurement_plan_portal/ (extension)
- **Purpose**: Portal interface for procurement plan viewing
- **Depends**: procurement_plan, portal
- **Models**: Portal access controls
- **Views**: Portal templates

### procurement_method_no_security/ (extension)
- **Purpose**: Removes security restrictions on procurement methods
- **Depends**: procurement_method
- **Models**: Security rule overrides
- **Views**: None

### procurement_type_no_security/ (extension)
- **Purpose**: Removes security restrictions on procurement types
- **Depends**: procurement_type
- **Models**: Security rule overrides
- **Views**: None
