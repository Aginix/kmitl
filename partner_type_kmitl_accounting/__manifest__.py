# -*- coding: utf-8 -*-
{
    'name': 'Partner Type (KMITL) - Accounting Bridge',
    'version': '16.0.1.0.0',
    'summary': 'Adds accounting settings (payable/receivable/WHT) to partner type',
    'author': 'KMITL',
    'website': 'https://www.kmitl.ac.th',
    'category': 'KMITL/Accounting',
    'license': 'LGPL-3',
    'depends': ['partner_type_kmitl', 'account', 'l10n_th_account_tax'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_type_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
