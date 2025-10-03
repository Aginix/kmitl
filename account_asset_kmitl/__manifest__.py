# -*- coding: utf-8 -*-
{
    'name': 'Account asset kmitl',
    'version': '16.0.1.0.0',
    'summary': """ Account asset kmitl Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['l10n_th_gov_account_asset_management', 'account_asset_operating_unit', 'account_fiscal_year', 'operating_unit_base_department'],
    "data": [
        "views/account_asset_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
