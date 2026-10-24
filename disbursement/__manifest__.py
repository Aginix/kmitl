# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement",
    "version": "16.0.16.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": [
        "account",
        "account_analytic_kmitl",
        "account_fiscal_year_enhance",
        "base_exception",
        "l10n_th_account_tax",
        "base_fontawesome",
        "partner_type_kmitl_accounting",
        "mail_activity_todo",
        # hr.employee.signature image + job_title for the printed signature block
        "hr_employee_digitized_signature",
        "thai_date_utils",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/mail_activity_type_data.xml",
        "data/exception_rule_data.xml",
        "wizards/disbursement_exception_confirm.xml",
        "wizards/return_request_wizard_views.xml",
        "views/disbursement_request_views.xml",
        "views/disbursement_return_views.xml",
        "views/exception_rule_views.xml",
    ],
    "installable": True,
    "application": True,
}
