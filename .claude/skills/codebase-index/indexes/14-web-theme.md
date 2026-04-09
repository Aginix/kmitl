# 14-web-theme
> 7 modules | Web interface customizations and theming

## Module Map

### theme_kmitl/ (application)
- **Purpose**: KMITL website theme
- **Depends**: website, theme_common
- **Models**: None
- **Views**: Theme templates and assets

### theme_common/ (extension)
- **Purpose**: Common theme components
- **Depends**: website
- **Models**: None
- **Views**: Shared theme elements

### web_kmitl/ (extension)
- **Purpose**: Web interface customizations
- **Depends**: web
- **Models**: None
- **Views**: Custom web components

### web_theme_classic_extended/ (extension)
- **Purpose**: Extended classic theme
- **Depends**: web_theme_classic
- **Models**: None
- **Views**: Extended theme views

### web_fiscal_year_systray/ (extension)
- **Purpose**: Fiscal year indicator in systray
- **Depends**: web, account_fiscal_year
- **Models**: Systray widget
- **Views**: Systray component

### web_login_thaid/ (extension)
- **Purpose**: Thai date display in login
- **Depends**: web, thai_date_utils
- **Models**: None
- **Views**: Login page modifications

### iframe_viewer_widget/ (extension)
- **Purpose**: Iframe viewer widget for web forms
- **Depends**: web
- **Models**: Widget component
- **Views**: Iframe widget
