# 15-localization
> 10+ modules | Thai localization and date utilities

## Module Map

### l10n_th_base_sequence/ (application)
- **Purpose**: Thai base sequence numbering
- **Depends**: l10n_th
- **Models**: Sequence customizations
- **Views**: None

### l10n_th_bank_payment_export_*/ (extensions)
- **Purpose**: Bank payment export for Thai banks (BAY, KTB, SCB)
- **Depends**: l10n_th, account_payment
- **Models**: Bank-specific export formats
- **Views**: Export wizards

### l10n_th_gov_account_asset_management/ (extension)
- **Purpose**: Government asset management localization
- **Depends**: l10n_th, account_asset
- **Models**: Government compliance fields
- **Views**: Asset management views

### l10n_th_gov_purchase_guarantee/ (extension)
- **Purpose**: Government purchase guarantee localization
- **Depends**: l10n_th, purchase_guarantee_kmitl
- **Models**: Government guarantee formats
- **Views**: Guarantee views

### l10n_th_gov_purchase_request/ (extension)
- **Purpose**: Government purchase request localization
- **Depends**: l10n_th, purchase_request_kmitl
- **Models**: Government PR formats
- **Views**: PR views

### l10n_th_gov_gpsc/ (extension)
- **Purpose**: GPSC (Government Procurement Service Center) integration
- **Depends**: l10n_th
- **Models**: GPSC compliance
- **Views**: GPSC interface

### thai_date_utils/ (extension)
- **Purpose**: Thai date utilities and formatting
- **Depends**: web
- **Models**: Date utility functions
- **Views**: Date widgets
