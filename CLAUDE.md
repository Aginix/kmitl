# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Note:** Do not automatically run testing or code quality commands. Only execute these when explicitly requested by the user.

### Testing (Run only when requested)
- Run all tests: `oca_run_tests`
- Initialize test database: `oca_init_test_database`
- Install addons and dependencies: `oca_install_addons`
- Check licenses: `manifestoo -d . check-licenses`
- Check development status: `manifestoo -d . check-dev-status --default-dev-status=Beta`

### Code Quality (Run only when requested)
- Run pre-commit checks: `pre-commit run --all-files --show-diff-on-failure --color=always`
- Install pre-commit: `pip install pre-commit`

## Architecture Overview

This is a collection of custom Odoo modules for KMITL (King Mongkut's Institute of Technology Ladkrabang), built on Odoo 16.0. The repository follows OCA (Odoo Community Association) standards and patterns.

### Core Module Architecture

**Budget System (`budget/`)**
- Core budgeting functionality with double-entry accounting principles
- Key models: `budget.move`, `budget.transfer`, `budget.account`, `budget.commitment`
- Features approval workflows, availability checking, and audit trails
- Implements state lifecycles: draft → review → posted → cancel
- Interactive reporting with JavaScript components in `static/src/components/`

**Account Analytics (`account_analytic_*`)**
- Enhanced analytic accounting for KMITL
- Hierarchical account structure with codes and sequences
- Integration with budget system for multi-dimensional reporting

**Procurement Planning (`procurement_plan/`)**
- Annual procurement planning with budget integration
- Payment scheduling and tracking
- Links to budget accounts for financial control

**Web Customizations (`web_*`)**
- KMITL-specific theming and UI customizations
- Mobile-responsive interface modifications
- Custom SCSS variables and component styling

### Module Structure Pattern

Each Odoo module follows this structure:
```
module_name/
├── __init__.py                 # Module initialization
├── __manifest__.py            # Module metadata and dependencies
├── models/                    # Python business logic
├── views/                     # XML UI definitions
├── data/                      # Master data and configuration
├── security/                  # Access control rules
├── static/src/                # JavaScript/CSS frontend assets
├── i18n/                      # Translation files
└── README.rst                 # Module documentation
```

### Key Dependencies

- Base Odoo 16.0 with standard accounting modules
- OCA community modules (account-*, server-*)
- Custom Thai localization (`l10n_th_*`)
- Financial and budgeting extensions

### Integration Points

**Budget-Accounting Integration:**
- Budget moves create accounting entries automatically
- Analytic accounts provide departmental/project tracking
- Double-entry principles ensure fiscal accuracy

**Approval Workflows:**
- Multi-step approval processes with email notifications
- State-based security and user permissions
- Complete audit trails via mail.thread inheritance

**Reporting Architecture:**
- Interactive JavaScript components for dynamic reports
- Server-side report generation with custom templates
- Export capabilities to various formats

### Development Standards

- Follow OCA coding standards and pre-commit hooks
- Use proper Odoo ORM patterns and security decorators
- Implement comprehensive logging with Python logging module
- Write descriptive docstrings explaining business purpose
- Use proper state management and validation in models