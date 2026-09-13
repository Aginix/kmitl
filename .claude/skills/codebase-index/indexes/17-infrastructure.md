# 17-infrastructure
> 10+ modules | Infrastructure and base system customizations

## Module Map

### operating_unit_kmitl/ (application)
- **Purpose**: Operating unit management for KMITL
- **Depends**: operating_unit, account_analytic_kmitl
- **Models**:
  - `operating.unit` → Extended OU model
    - Key fields: code, analytic_account_id
- **Views**: operating_unit_views.xml

### partner_* (extensions)
- **Purpose**: Partner and contact management enhancements
- **Depends**: contacts, base
- **Models**: Extended partner fields
- **Views**: Partner views

### contacts_* (extensions)
- **Purpose**: Contact management customizations
- **Depends**: contacts
- **Models**: Contact extensions
- **Views**: Contact views

### base_tier_validation_comment/ (extension)
- **Purpose**: Comments in tier validation
- **Depends**: base_tier_validation
- **Models**: Comment fields in approvals
- **Views**: Validation comment views

### website_menu_restriction/ (extension)
- **Purpose**: Website menu access restrictions
- **Depends**: website
- **Models**: Menu security rules
- **Views**: Menu restriction views

### field_management/ (extension)
- **Purpose**: Dynamic field management
- **Depends**: base
- **Models**: Field visibility controls
- **Views**: Field management interface

### product_hide_fields/ (extension)
- **Purpose**: Hide product fields based on permissions
- **Depends**: product
- **Models**: Field visibility logic
- **Views**: Modified product views

### remove_powered_by_odoo/ (extension)
- **Purpose**: Remove Odoo branding
- **Depends**: web
- **Models**: None
- **Views**: Branding removal

### i18n_th_account/ (extension)
- **Purpose**: Thai translations for accounting
- **Depends**: account
- **Models**: None
- **Views**: Thai account labels

### i18n_th_purchase/ (extension)
- **Purpose**: Thai translations for purchase
- **Depends**: purchase
- **Models**: None
- **Views**: Thai purchase labels
