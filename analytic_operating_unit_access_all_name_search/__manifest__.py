# Copyright 2026 KMITL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Analytic OU Access - Name Search Filter",
    "summary": "Filter analytic account lookups by user's operating units, "
    "with a per-field context bypass",
    "version": "16.0.1.0.0",
    "author": "KMITL",
    "category": "Sales",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/operating-unit",
    "depends": ["analytic_operating_unit_access_all"],
    "data": [
        "security/analytic_security.xml",
    ],
    "installable": True,
}
