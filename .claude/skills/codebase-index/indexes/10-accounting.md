# 10-accounting
> 12+ modules | Accounting customizations and asset management

## Module Map

### account_kmitl/ (application)
- **Purpose**: Core accounting customizations for KMITL
- **Depends**: account, account_analytic_kmitl
- **Models**:
  - `account.move` → Extended with KMITL fields
    - Key fields: analytic_distribution, fiscal_year_id
- **Views**: account_move_views.xml

### account_move_kmitl/ (extension)
- **Purpose**: Additional account move customizations
- **Depends**: account_kmitl
- **Models**: Extended move functionality
- **Views**: Enhanced move views

### account_move_request/ (extension)
- **Purpose**: Account move request system
- **Depends**: account_kmitl
- **Models**:
  - `account.move.request` → Move request model
    - States: draft → approved → posted
    - Key methods: action_approve(), action_post_move()
- **Views**: Move request views

### account_payment_kmitl/ (extension)
- **Purpose**: Payment customizations
- **Depends**: account_kmitl, account_payment
- **Models**: Extended payment features
- **Views**: Payment views

### account_asset_kmitl/ (extension)
- **Purpose**: Asset management customizations
- **Depends**: account_asset, account_analytic_kmitl
- **Models**:
  - `account.asset` → Extended asset model
    - Key fields: analytic_distribution, operating_unit_id
- **Views**: Asset views

### account_asset_batch/ (extension)
- **Purpose**: Batch asset operations
- **Depends**: account_asset_kmitl
- **Models**: Batch processing
- **Views**: Batch operation views

### account_asset_depreciation_board/ (extension)
- **Purpose**: Depreciation board for assets
- **Depends**: account_asset_kmitl
- **Models**: Depreciation tracking
- **Views**: Depreciation board

### account_asset_operating_unit/ (extension)
- **Purpose**: Operating unit support for assets
- **Depends**: account_asset_kmitl, operating_unit
- **Models**: OU restrictions
- **Views**: OU asset views

### account_asset_purchase/ (extension)
- **Purpose**: Purchase integration for assets
- **Depends**: account_asset_kmitl, purchase_kmitl
- **Models**: Purchase-to-asset links
- **Views**: Purchase asset views

### account_fiscal_year_all_user/ (extension)
- **Purpose**: Fiscal year access for all users
- **Depends**: account_fiscal_year
- **Models**: Access control
- **Views**: None

### account_fiscal_year_enhance/ (extension)
- **Purpose**: Enhanced fiscal year management
- **Depends**: account_fiscal_year
- **Models**: Additional features
- **Views**: Fiscal year views

### account_journal_kmitl/ (extension)
- **Purpose**: Journal customizations
- **Depends**: account_kmitl
- **Models**: Journal extensions
- **Views**: Journal views
