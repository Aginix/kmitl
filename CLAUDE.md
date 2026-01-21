# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Philosophy

Think carefully and only action the specific task I have given you with the most concise and elegant solution that changes as little code as possible

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

## Git Branch and PR Naming Conventions

Following [OCA Contributing Guidelines](https://github.com/OCA/odoo-community.org/blob/master/website/Ede/contribute/CONTRIBUTING.rst).

### Branch Naming
Branches must follow the OCA pattern: `{version}-{type}-{module_name}-{short_description}`

**Type prefixes (lowercase):**
- `add`: New features or modules
- `imp`: Improvements to existing features
- `fix`: Bug fixes
- `mig`: Migration to new Odoo version
- `ref`: Code refactoring (no functional changes)
- `rem`: Removal of deprecated features

**Examples:**
- `16.0-fix-budget-nan_value_in_report`
- `16.0-add-account_analytic_kmitl-dimension_filter`
- `16.0-imp-procurement_plan-performance_optimization`
- `16.0-mig-budget-migration_to_16`
- `16.0-ref-account_move-cleanup_deprecated_methods`

### Pull Request Naming
PR titles must follow the OCA pattern: `[{version}][{TYPE}] {module_name}: {description}`

**Type prefixes (UPPERCASE):**
- `ADD`: New features or modules
- `IMP`: Improvements to existing features
- `FIX`: Bug fixes
- `MIG`: Migration to new Odoo version
- `REF`: Code refactoring (no functional changes)
- `REM`: Removal of deprecated features

**Examples:**
- `[16.0][FIX] budget: fix NaN value in report`
- `[16.0][ADD] account_analytic_kmitl: add financial dimension framework`
- `[16.0][IMP] budget: improve transfer approval workflow`
- `[16.0][MIG] procurement_plan: migration to 16.0`
- `[16.0][REF] account_move: refactor validation logic`

## Architecture Overview

This is a collection of custom Odoo modules for KMITL (King Mongkut's Institute of Technology Ladkrabang), built on Odoo 16.0. The repository follows OCA (Odoo Community Association) standards and patterns.

### Core Module Architecture

**Budget System (`budget/`)**
- Core budgeting functionality with double-entry accounting principles
- Key models: `budget.move`, `budget.transfer`, `budget.account`, `budget.commitment`
- Features approval workflows, availability checking, and audit trails
- Implements state lifecycles: draft → review → posted → cancel
- Interactive reporting with JavaScript components in `static/src/components/`

**Account Analytics (`account_analytic_*`) - Financial Dimensions Framework**

The analytic account system implements a **4-dimensional financial analysis framework** that serves as the foundation for KMITL's financial tracking and reporting:

#### Core Modules
- `account_analytic_plan_code`: Adds unique codes to analytic plans for identification
- `account_analytic_seq`: Provides sequence-based ordering for hierarchical display
- `account_analytic_kmitl`: Main integration module implementing the 4D framework

#### Four Financial Dimensions

1. **Activities (กิจกรรม)** - `activities`
   - Tracks governmental programs and activities
   - Hierarchical structure with codes like `090070101` (Education Support)
   - Supports deep organizational hierarchies (up to 11-digit codes)

2. **Departments (หน่วยงาน)** - `departments`
   - Organizational unit tracking across faculties and offices
   - Examples: `01` (Engineering), `89` (Rector's Office)
   - Hierarchical structure for sub-departments

3. **Funds (กองทุน)** - `funds`
   - Fund source classification and tracking
   - Examples: `0100` (General Fund), `0200` (Education Fund)
   - Hierarchical fund categories with sub-funds

4. **Sources (แหล่งเงิน)** - `sources`
   - Money source classification
   - Examples: `1` (Government Budget), `2` (Revenue Budget)
   - Flat classification structure

#### Technical Implementation
- **AnalyticDistributionMixin**: Converts JSON distribution to discrete dimension fields
- **Hierarchical Budget Matching**: Parent appropriations can cover child commitments
- **Domain Filtering**: Ensures data integrity across dimensions
- **Performance Optimized**: Strategic indexing and computed fields for efficiency

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

**Financial Dimensions Integration:**
- **Budget Moves**: Direct dimension fields (`department_analytic_id`, `source_analytic_id`)
- **Budget Move Lines**: Full 4D analytic distribution on each line item
- **Budget Controller**: Hierarchical matching algorithm for parent-child appropriations
- **Cross-dimensional Analysis**: Budget analysis across all four dimensions
- **Government Compliance**: Aligned with Thai government accounting standards

**Approval Workflows:**
- Multi-step approval processes with email notifications
- State-based security and user permissions
- Complete audit trails via mail.thread inheritance

**Reporting Architecture:**
- Interactive JavaScript components for dynamic reports
- Server-side report generation with custom templates
- Export capabilities to various formats

### Working with Financial Dimensions

When developing features that interact with financial data:

**Using the AnalyticDistributionMixin:**
```python
# The mixin automatically provides dimension fields
department_analytic_id  # Many2one to department dimension
activity_analytic_id    # Many2one to activity dimension
fund_analytic_id        # Many2one to fund dimension
source_analytic_id      # Many2one to source dimension
```

**Domain Filtering for Dimensions:**
```python
# Ensure correct dimension selection
domain=[("root_plan_id.code", "=", "activities")]   # For activities
domain=[("root_plan_id.code", "=", "departments")]  # For departments
```

**Hierarchical Budget Matching:**
- Parent-level appropriations automatically cover child-level commitments
- Use `parent_path` for efficient hierarchical queries
- The budget controller handles complex matching scenarios

**Key Models to Understand:**
- `account.analytic.account`: Extended with hierarchy and sequences
- `account.analytic.plan`: Enhanced with unique codes
- `budget.move` & `budget.move.line`: Full 4D dimension tracking
- `AnalyticDistributionMixin`: Core mixin for dimension fields

### Development Standards

- Follow OCA coding standards and pre-commit hooks
- Use proper Odoo ORM patterns and security decorators
- Implement comprehensive logging with Python logging module
- Write descriptive docstrings explaining business purpose
- Use proper state management and validation in models
- When working with analytic dimensions, always use the provided mixins and domain filters

## Git Commit Guidelines

Following [OCA Commit Message Guidelines](https://github.com/OCA/odoo-community.org/blob/master/website/Ede/contribute/CONTRIBUTING.rst).

### Commit Message Format
```
[{TYPE}] {module_name}: {short description}

{Optional longer description explaining the change.}
```

**Type prefixes (UPPERCASE):**
- `[ADD]`: New features or modules
- `[IMP]`: Improvements to existing features
- `[FIX]`: Bug fixes
- `[MIG]`: Migration to new Odoo version
- `[REF]`: Code refactoring (no functional changes)
- `[REM]`: Removal of deprecated features
- `[I18N]`: Translation updates

**Examples:**
```
[FIX] budget: fix NaN value when amount is zero

The budget report was showing NaN when the amount field was empty.
Added a default value of 0.0 to prevent this issue.
```

```
[ADD] account_analytic_kmitl: add 4-dimensional financial framework

Implements the four financial dimensions required by KMITL:
- Activities (กิจกรรม)
- Departments (หน่วยงาน)
- Funds (กองทุน)
- Sources (แหล่งเงิน)
```

### Do NOT Include
- `🤖 Generated with [Claude Code](https://claude.com/claude-code)` footer
- `Co-Authored-By: Claude` lines
- Emojis in commit messages
