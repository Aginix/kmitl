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

### Branch Naming
Branches must follow the pattern: `16.0-{type}-{module_name}`

**Type prefixes:**
- `imp`: Improvements to existing features
- `add`: New features or modules
- `mig`: Migration-related changes
- `fix`: Bug fixes

**Examples:**
- `16.0-fix-budget-some-bug`
- `16.0-add-account_analytic_kmitl-dimension-filter`
- `16.0-imp-procurement_plan-performance`

### Pull Request Naming
PR titles must follow the pattern: `[16.0][TYPE] module_name: description`

**Examples:**
- `[16.0][FIX] budget: fix NaN value in report`
- `[16.0][ADD] account_analytic_kmitl: add financial dimension framework`
- `[16.0][IMP] budget: improve transfer approval workflow`

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

The analytic account system implements a **6-dimensional financial analysis framework** that serves as the foundation for KMITL's financial tracking and reporting. All dimensions are stored in the `analytic_distribution` JSON field.

#### Core Modules
- `account_analytic_plan_code`: Adds unique codes to analytic plans for identification
- `account_analytic_seq`: Provides sequence-based ordering for hierarchical display
- `account_analytic_kmitl`: Main integration module implementing the 6D framework

#### Six Financial Dimensions

1. **Departments (ส่วนงาน)** - `departments`
   - Organizational unit tracking across faculties and offices
   - Examples: `01` (Engineering), `89` (Rector's Office)
   - Hierarchical structure for sub-departments

2. **Sources (แหล่งเงิน)** - `sources`
   - Money source classification
   - Examples: `1` (Government Budget), `2` (Revenue Budget)
   - Flat classification structure

3. **Funds (กองทุน)** - `funds`
   - Fund source classification and tracking
   - Examples: `0100` (General Fund), `0200` (Education Fund)
   - Hierarchical fund categories with sub-funds

4. **Activities (ด้าน/แผนงาน/กิจกรรม)** - `activities`
   - Tracks governmental programs and activities
   - Hierarchical structure with codes like `090070101` (Education Support)
   - Supports deep organizational hierarchies (up to 11-digit codes)

5. **KMITL Projects (โครงการ/กิจกรรม)** - `kmitl_project`
   - Project/activity tracking
   - Analytic account is assigned only after budget allocation (not at creation)

6. **Procurement Plan (แผนจัดซื้อจัดจ้าง)** - `procurement_plan`
   - Procurement planning dimension
   - Analytic account is assigned only after budget allocation (not at creation)

#### Technical Implementation
- **`analytic_distribution`**: The primary JSON field for storing all dimension data. All data transfer between models and usage must go through this field.
- **Convenience `*_analytic_id` fields**: Some models provide computed Many2one fields (e.g., `department_analytic_id`, `source_analytic_id`, `fund_analytic_id`, `activity_analytic_id`) for display (compute) and easy input (inverse). These are derived from `analytic_distribution` — never use them as the source of truth for data transfer.
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
- **`analytic_distribution`**: The single source of truth for all 6 dimensions, used for data transfer between models
- **Convenience fields**: `department_analytic_id`, `source_analytic_id`, etc. are computed/inverse helpers for UI only
- **Budget Controller**: Hierarchical matching algorithm for parent-child appropriations
- **Cross-dimensional Analysis**: Budget analysis across all six dimensions
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

**Analytic Distribution (source of truth):**
```python
# analytic_distribution is the primary field — always use it for data transfer
# Format: {"analytic_account_id": percentage, ...}
analytic_distribution = {"42": 100, "55": 100, "78": 100}
```

**Convenience fields (UI helpers only):**
```python
# Some models provide computed Many2one fields derived from analytic_distribution
department_analytic_id  # compute/inverse from analytic_distribution
activity_analytic_id    # compute/inverse from analytic_distribution
fund_analytic_id        # compute/inverse from analytic_distribution
source_analytic_id      # compute/inverse from analytic_distribution
# These are for display and easy input — never use them for data transfer
```

**Domain Filtering for Dimensions:**
```python
# Ensure correct dimension selection
domain=[("root_plan_id.code", "=", "activities")]       # ด้าน/แผนงาน/กิจกรรม
domain=[("root_plan_id.code", "=", "departments")]      # ส่วนงาน
domain=[("root_plan_id.code", "=", "funds")]            # กองทุน
domain=[("root_plan_id.code", "=", "sources")]          # แหล่งเงิน
domain=[("root_plan_id.code", "=", "kmitl_project")]    # โครงการ/กิจกรรม
domain=[("root_plan_id.code", "=", "procurement_plan")] # แผนจัดซื้อจัดจ้าง
```

**Hierarchical Budget Matching:**
- Parent-level appropriations automatically cover child-level commitments
- Use `parent_path` for efficient hierarchical queries
- The budget controller handles complex matching scenarios

**Key Models to Understand:**
- `account.analytic.account`: Extended with hierarchy and sequences
- `account.analytic.plan`: Enhanced with unique codes
- `budget.move` & `budget.move.line`: Full 6D dimension tracking via `analytic_distribution`
- `AnalyticDistributionMixin`: Core mixin providing convenience dimension fields

### Development Standards

- Follow OCA coding standards and pre-commit hooks
- Use proper Odoo ORM patterns and security decorators
- Implement comprehensive logging with Python logging module
- Write descriptive docstrings explaining business purpose
- Use proper state management and validation in models
- When working with analytic dimensions, always use the provided mixins and domain filters

## Git Commit Guidelines

When committing changes, do NOT include:
- `🤖 Generated with [Claude Code](https://claude.com/claude-code)` footer
- `Co-Authored-By: Claude` lines

Commit messages should follow standard OCA format:
```
[TYPE] module_name: short description

Optional longer description if needed.
```
