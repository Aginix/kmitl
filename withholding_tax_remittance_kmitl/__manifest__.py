# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Withholding Tax Remittance KMITL",
    "version": "16.0.1.0.0",
    "category": "KMITL/Finance",
    "summary": "Batch-clear the withholding tax payable (รอนำส่ง) when it is remitted to the Revenue Department",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "finance_kmitl",
        "l10n_th_account_tax",
        "accounting_kmitl",
        "thai_date_utils",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/withholding_tax_cert_views.xml",
        "views/withholding_tax_remittance_views.xml",
    ],
    "installable": True,
    "application": False,
}
