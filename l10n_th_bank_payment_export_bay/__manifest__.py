# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Thai Localization - Bank Payment Export BAY",
    "version": "16.0.1.1.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-thailand",
    "license": "AGPL-3",
    "category": "Localization / Accounting",
    "summary": "Bank Payment Export File BAY (Krungsri)",
    "depends": ["l10n_th_bank_payment_export_format"],
    "data": [
        "data/bank.export.format.csv",
        "data/bank.export.format.line.csv",
        "data/bank_payment_template.xml",
        "views/bank_payment_export_view.xml",
    ],
    "installable": True,
    "development_status": "Alpha",
    "maintainers": ["Saran440"],
}
