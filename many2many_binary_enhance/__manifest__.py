# -*- coding: utf-8 -*-
{
    'name': 'Many2Many Binary Enhance',
    'version': '16.0.1.0.0',
    'summary': 'Add edit functionality to many2many_binary widget',
    'author': 'KMITL',
    'website': '',
    'category': 'Technical',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/attachment_name_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'many2many_binary_enhance/static/src/fields/many2many_binary_enhance/many2many_binary_enhance.js',
            'many2many_binary_enhance/static/src/fields/many2many_binary_enhance/many2many_binary_enhance.xml',
        ],
    },
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
