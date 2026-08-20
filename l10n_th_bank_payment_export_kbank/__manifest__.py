# Copyright 2024 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Thai Localization - Bank Payment Export KBANK",
    "version": "16.0.1.1.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "AGPL-3",
    "category": "Localization / Accounting",
    "summary": "Bank Payment Export File KBANK (Kasikornbank)",
    "depends": ["l10n_th_bank_payment_export_format"],
    "data": [
        "data/bank.export.format.csv",
        "data/bank.export.format.line.csv",
        "data/bank_payment_template.xml",
        "views/bank_payment_export_view.xml",
    ],
    "installable": True,
    "development_status": "Alpha",
}
