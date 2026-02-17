===============
Budget Project
===============

This module integrates KMITL projects with the budget system by adding project-related
configuration to budget accounts.

Features
========

* Configure budget accounts to support project/activity types
* Define project types for budget accounts (research, education, service, etc.)
* Integrate with the 6-dimensional financial framework (account_analytic_kmitl)
* Link budget accounts with KMITL project management

Configuration
=============

1. Go to Budgeting → Configuration → Budget Accounts
2. Enable "Enable Project/Activity" checkbox on budget accounts that should support project management
3. Select the appropriate project type for the budget account
4. Only budget accounts with this configuration will be available for project budget allocation

Usage
=====

**Configuring Budget Accounts for Projects:**

1. Navigate to Budgeting → Configuration → Budget Accounts
2. Open a budget account or create a new one
3. In the "Project" section, check "Enable Project/Activity"
4. Select the project type (research, education, service, etc.)
5. Save the configuration

**Integration with KMITL Projects:**

The module extends budget accounts with project configuration that integrates with the
kmitl_project module. When a budget account has project enabled:

* The account becomes available for project budget allocation
* Project types help categorize budget usage by activity type
* Financial dimensions are tracked through the analytic distribution framework

Technical Details
=================

* Depends on: budget, account_analytic_kmitl, kmitl_project
* Extends: budget.account model with project fields
* Provides: Project type configuration and project enablement flags

Credits
=======

Contributors
------------

* KMITL Development Team