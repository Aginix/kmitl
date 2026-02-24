# -*- coding: utf-8 -*-
{
    'name': 'Account Asset Depreciation Report',
    'version': '16.0.1.0.0',
    'summary': 'รายงานสำรวจทรัพย์สินและค่าเสื่อมราคา',
    'category': 'KMITL',
    'author': 'Aginix Technologies',
    'website': 'https://github.com/aginix/kmitl',
    'depends': ['account_asset_kmitl', 'account_asset_usability_kmitl', 'account_fiscal_year'],
    'external_dependencies': {'python': ['xlsxwriter']},
    'data': [
        'security/ir.model.access.csv',
        'views/asset_depreciation_report_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
