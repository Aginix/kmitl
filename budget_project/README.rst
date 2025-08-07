===============
Budget Project
===============

This module adds project/activity budgeting capabilities to the KMITL budget system.

Features
========

* Create and manage budget projects/activities
* Link projects to specific budget accounts  
* Track project budgets with 4-dimensional financial dimensions
* Integrate with budget move lines for project allocation
* State workflow: draft → confirmed → done

Configuration
=============

1. Go to Budgeting → Configuration → Budget Accounts
2. Enable "Enable Project/Activity" checkbox on budget accounts that should support project management
3. Only budget accounts with this flag enabled will be available for project creation

Usage
=====

**Creating Projects/Activities:**

1. Go to Budgeting → Projects/Activities
2. Create a new project with name, budget amount, and budget account
3. Set financial dimensions (department, activity, fund, source)
4. Assign responsible user and set project dates

**Managing Projects from Budget Moves:**

1. When creating a budget appropriation, select a budget move line
2. If the budget account has project enabled, a "Projects/Activities" tab will appear
3. Create and manage projects directly from the budget move line form
4. Projects will automatically inherit financial dimensions from the budget line

**Project States:**

* Draft: Initial state for new projects
* Confirmed: Project is approved and active
* Done: Project is completed
* Cancelled: Project is cancelled

Known Issues / Roadmap
======================

* Future: Add project budget consumption tracking
* Future: Integration with procurement and accounting
* Future: Project reporting and analytics

Credits
=======

Contributors
------------

* KMITL Development Team