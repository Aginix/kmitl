---
name: codebase-index
description: "Codebase index and architecture map for the Odoo Project (KMITL/AGX). MANDATORY: Read this before searching the actual code to locate file paths."
metadata:
  version: "1.0"
  project: "odoo-doodba"
---

# Codebase Index Skill

## 🚨 MANDATORY WORKFLOW (AI Instructions)
1. **DO NOT** use broad search commands (e.g., `grep -r`) initially.
2. **MUST** read this `SKILL.md` file to identify the relevant Domain from the "Domain Lookup Table".
3. **OPEN** the corresponding index file (e.g., `indexes/01-budget-core.md`) to find model names, file paths, and relationships.
4. **NAVIGATE** directly to the specific `.py` or `.xml` file once the exact path is identified.

## 🗺️ Domain Lookup Table
| Keyword / Feature | Index File |
|-------------------|------------|
| Budget, Appropriations, Budget Demo | `indexes/01-budget-core.md` |
| Budget Appropriations, Summary | `indexes/02-budget-appropriation.md` |
| Budget Reports, OU, Project, Product | `indexes/03-budget-extensions.md` |
| Analytic Account, Dimensions, Tags | `indexes/04-analytic-dimensions.md` |
| Procurement Plan, Method, Type | `indexes/05-procurement-plan.md` |
| Purchase Request (PR) | `indexes/06-purchase-request.md` |
| Purchase Order (PO), Purchase KMITL | `indexes/07-purchase-order.md` |
| Work Acceptance, Guarantees, Invoice Plan | `indexes/08-purchase-acceptance.md` |
| Disbursement, AGX Approval | `indexes/09-disbursement.md` |
| Accounting, KMITL Account, Asset, Payments | `indexes/10-accounting.md` |
| Stock, Inventory, Warehouses | `indexes/11-stock-inventory.md` |
| HR, Employee, Recruitment, AGX HRMS | `indexes/12-hr-employee.md` |
| Project, Construction | `indexes/13-project.md` |
| Web, Themes, UI, Iframe Widget | `indexes/14-web-theme.md` |
| Thai Localization, Date Utils | `indexes/15-localization.md` |
| Sarabun, Approvals, Office Orders | `indexes/16-approval-sarabun.md` |
| Contacts, Partner, Tier, Website Menu | `indexes/17-infrastructure.md` |
| OCA Modules, Odoo Core Source Code | `indexes/18-oca-odoo-source.md` |

## 🔗 Cross-Reference Quick Map
- `purchase.request` (06) -> `purchase.order` (07) -> `purchase.work.acceptance` (08)
- `purchase.order` (07) -> `budget.appropriation` (02) -> `budget.core` (01)
- `account.move` (10) -> `analytic.account` (04) / `operating.unit` (17)
- `agx.approval.*` (16) -> Spans across multiple models (PR, PO, Disbursement)

## 📁 Full Source Directory Map
- **Custom Modules:** `.../odoo-doodba/odoo/custom/src/` (See details in `indexes/18-oca-odoo-source.md`)

## 🔄 How to Update
When creating a new module, add it to the `Domain Lookup Table` above and update the corresponding `.md` file in the `indexes/` directory. Maintain a strict limit of 200 lines per index file to conserve tokens.
