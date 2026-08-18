# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Budget Expense Plan with Operating Units",
    "version": "16.0.1.0.0",
    "category": "KMITL/Budget",
    "summary": "จำกัดการเข้าถึงเอกสารแผนการเบิกจ่ายตาม Operating Unit",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "operating_unit",
        "budget_expense_plan",
    ],
    "data": [
        "security/budget_expense_plan_security.xml",
        "views/budget_expense_plan_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
