# 01-budget-core
> 4 modules | Core budget management modules for KMITL

## Module Map

### budget/ (application)
- **Purpose**: Core budget management system with hierarchical account structure, budget commitments, transfers, and Thai government accounting integration
- **Depends**: account, account_analytic_kmitl, account_fiscal_year, mail, l10n_th_base_sequence
- **Models**:
  - `budget.account` → `models/budget_account.py`
    - Key fields: code, name, parent_id, budget_type, fund_analytic_ids, budgetable
    - Key methods: action_view_children_accounts(), get_as_tree()
  - `budget.commitment` → `models/budget_commitment.py`
    - States: draft → review → approved → committed → released
    - Key fields: name, budget_account_id, analytic_account_id, amount, date
    - Key methods: action_approve(), action_commit(), action_release()
  - `budget.move` → `models/budget_move.py`
    - States: draft → posted
    - Key fields: name, journal_id, date, move_lines
    - Key methods: action_post(), action_draft()
  - `budget.transfer` → `models/budget_transfer.py`
    - States: draft → approved → done
    - Key fields: name, from_budget_account_id, to_budget_account_id, amount
    - Key methods: action_approve(), action_transfer()
- **Views**: budget_account_views.xml, budget_commitment_views.xml, budget_move_views.xml, budget_transfer_views.xml

### budget_demo/ (application)
- **Purpose**: Demo data for budget module including sample budget moves, commitments, and accounts
- **Depends**: account_analytic_kmitl, budget, kmitl_demo
- **Models**: None (data only)
- **Views**: None

### budget_account_mass_edit/ (extension)
- **Purpose**: Mass edit functionality for budget accounts using server actions
- **Depends**: budget, server_action_mass_edit
- **Models**: None
- **Views**: None

### budget_account_portal/ (extension)
- **Purpose**: Portal interface for budget account viewing and procurement plan integration
- **Depends**: budget, web, portal, procurement_plan_budget
- **Models**: None
- **Views**: portal_templates.xml, budget_account_views.xml

### budget_account_root/ (extension)
- **Purpose**: Root budget account management utilities
- **Depends**: budget
- **Models**: None
- **Views**: None
