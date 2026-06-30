# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "KMITL Budget Revenue Comparison Report",
    "version": "16.0.1.0.0",
    "category": "KMITL/Budget",
    "summary": "Configurable report comparing budgeted revenue with actual "
    "revenue (งบประมาณรายรับ vs รายรับจริง)",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "budget",
        "account",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/report_action_xlsx.xml",
        "views/budget_revenue_report_line_views.xml",
        "views/menuitem.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "budget_revenue_comparison/static/src/budget_revenue_comparison/multi_record_select.js",
            "budget_revenue_comparison/static/src/budget_revenue_comparison/budget_revenue_comparison.js",
            "budget_revenue_comparison/static/src/budget_revenue_comparison/budget_revenue_comparison.xml",
            "budget_revenue_comparison/static/src/budget_revenue_comparison/budget_revenue_comparison.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
}
