# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "KMITL Budget Expense Plan",
    "version": "16.0.1.0.0",
    "category": "KMITL/Budget",
    "summary": "แผนการเบิกจ่ายประจำปีงบประมาณ รายส่วนงาน เทียบกับผลเบิกจ่ายจริง",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "budget",
        "account_analytic_kmitl",
        "report_xlsx",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/report_action_xlsx.xml",
        "views/budget_expense_template_views.xml",
        "views/budget_expense_required_department_views.xml",
        "views/budget_expense_plan_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "budget_expense_plan/static/src/expense_plan_grid/expense_plan_grid.js",
            "budget_expense_plan/static/src/expense_plan_grid/expense_plan_grid.xml",
            "budget_expense_plan/static/src/expense_plan_grid/expense_plan_grid.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
}
