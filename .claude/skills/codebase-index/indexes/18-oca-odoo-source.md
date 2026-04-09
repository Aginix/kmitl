# 18-oca-odoo-source
> OCA repositories and Odoo core source reference

## OCA Repositories

### account-analytic (src/account-analytic/)
- **analytic_tag_dimension**: Multi-dimensional analytic tags
- **account_analytic_parent**: Hierarchical analytic accounts
- **account_analytic_plan_code**: Code field for analytic plans
- **account_analytic_seq**: Sequence ordering for analytics
- **analytic_operating_unit**: Operating unit integration

### account-budgeting (src/account-budgeting/)
- **account_budget_oca**: OCA budget management
- **budget_control**: Budget control on documents
- **budget_control_purchase**: Purchase budget control

### account-closing (src/account-closing/)
- **account_cutoff_base**: Base cutoff functionality
- **account_cutoff_accrual**: Accrual cutoffs
- **account_cutoff_prepaid**: Prepaid cutoffs

### account-financial-reporting (src/account-financial-reporting/)
- **account_financial_report**: Financial reports framework
- **customer_activity_statement**: Customer statements
- **partner_ledger**: Partner ledger reports

### account-financial-tools (src/account-financial-tools/)
- **account_asset_management**: Asset management
- **account_fiscal_year**: Fiscal year management
- **account_lock_date_update**: Lock date updates

### account-fiscal-rule (src/account-fiscal-rule/)
- **account_fiscal_rule**: Fiscal rules for accounts
- **account_fiscal_rule_purchase**: Purchase fiscal rules

### account-invoice-reporting (src/account-invoice-reporting/)
- **account_comment_template**: Invoice comment templates
- **account_invoice_report_due_list**: Due date reporting

### account-reconcile (src/account-reconcile/)
- **account_reconcile_oca**: Advanced reconciliation
- **account_statement_reconcile**: Statement reconciliation

### agreement (src/agreement/)
- **agreement**: Contract agreement management
- **agreement_sale**: Sale agreement integration

### hr (src/hr/)
- **hr_appraisal_oca**: Employee appraisals
- **hr_employee_firstname**: Employee name fields
- **hr_holidays_public**: Public holidays

### hr-holidays (src/hr-holidays/)
- **hr_holidays_auto_extend**: Auto-extend leaves
- **hr_holidays_credit**: Leave credits

### l10n-thailand (src/l10n-thailand/)
- **l10n_th**: Thai localization base
- **l10n_th_account**: Thai accounting
- **l10n_th_bank_payment**: Bank payment exports

### mis-builder (src/mis-builder/)
- **mis_builder**: Management Information System
- **mis_builder_budget**: MIS budget integration

### operating-unit (src/operating-unit/)
- **operating_unit**: Operating unit framework
- **account_operating_unit**: Accounting OU integration
- **sale_operating_unit**: Sales OU integration

### partner-contact (src/partner-contact/)
- **partner_contact_birthdate**: Birthdate field
- **partner_contact_gender**: Gender field
- **partner_contact_nationality**: Nationality field

### product-attribute (src/product-attribute/)
- **product_pricelist_direct_print**: Pricelist printing
- **product_variant_default_code**: Variant codes

### project (src/project/)
- **project_key**: Project key fields
- **project_role**: Project roles
- **project_stage**: Project stages

### purchase-workflow (src/purchase-workflow/)
- **purchase_request**: Purchase request system
- **purchase_order_line_menu**: PO line menu
- **purchase_blanket_order**: Blanket orders

### reporting-engine (src/reporting-engine/)
- **bi_sql_editor**: SQL report editor
- **report_async**: Async reporting
- **report_xlsx**: XLSX report format

### server-auth (src/server-auth/)
- **auth_saml**: SAML authentication
- **password_security**: Password policies

### server-backend (src/server-backend/)
- **base_technical_features**: Technical features
- **server_environment_data_encryption**: Data encryption

### server-brand (src/server-brand/)
- **disable_odoo_online**: Disable online features
- **server_brand**: Server branding

### server-tools (src/server-tools/)
- **auditlog**: Audit logging
- **base_technical_user**: Technical user
- **mass_editing**: Mass editing

### server-ux (src/server-ux/)
- **web_responsive**: Responsive web
- **web_timeline**: Timeline view

### social (src/social/)
- **mail_activity_board**: Activity board
- **mail_tracking**: Email tracking

### spreadsheet (src/spreadsheet/)
- **spreadsheet_dashboard**: Spreadsheet dashboards
- **spreadsheet_oca**: OCA spreadsheet integration

### stock-logistics-warehouse (src/stock-logistics-warehouse/)
- **stock_request**: Stock request system
- **stock_inventory_discrepancy**: Inventory discrepancy
- **stock_picking_batch**: Batch picking

### web (src/web/)
- **web_advanced_search**: Advanced search
- **web_domain_field**: Domain fields
- **web_widget_color**: Color widgets

### website (src/website/)
- **website_analytics_matomo**: Matomo analytics
- **website_crm**: Website CRM integration

## Odoo Core Source

### Core Addons (src/odoo/addons/)
- **account**: Accounting module
- **sale**: Sales management
- **purchase**: Purchase management
- **stock**: Inventory management
- **hr**: Human resources
- **project**: Project management
- **website**: Website builder

### Base Framework (src/odoo/odoo/)
- **models**: ORM models
- **fields**: Field types
- **api**: Decorator API
- **tools**: Utility functions
- **http**: Web framework
- **addons**: Module system

### Standard Modules
- **mail**: Email and messaging
- **base**: Base functionality
- **web**: Web interface
- **contacts**: Contact management
- **product**: Product management
