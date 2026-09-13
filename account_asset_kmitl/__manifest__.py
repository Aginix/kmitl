# -*- coding: utf-8 -*-
{
    'name': 'Account Asset KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Account asset kmitl Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['l10n_th_gov_account_asset_management', 'account_asset_operating_unit', 'account_fiscal_year', 'l10n_th_gov_gpsc', 'account_kmitl', 'account_asset_number', 'portal', 'account_analytic_kmitl', 'user_role_purchase'],
    "data": [
        "data/res.users.role.xml",
        "data/account_asset_profile.xml",
        "views/menuitem.xml",
        "views/account_asset_views.xml",
        "views/purchase_order_views.xml",
        "views/template_asset_number.xml",
        "views/template_portal.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
