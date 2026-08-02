# -*- coding: utf-8 -*-
{
    'name': 'L10n Th Bank Payment Export Format',
    'version': '16.0.1.0.1',
    'summary': """ L10n Th Bank Payment Export Format Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['l10n_th_bank_payment_export'],
    "data": [
        "security/ir.model.access.csv",
        "views/bank_export_format_views.xml",
        "views/bank_payment_export_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
