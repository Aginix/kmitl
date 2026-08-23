# -*- coding: utf-8 -*-
{
    'name': 'Partner Type (KMITL)',
    'version': '16.0.1.0.0',
    'summary': 'Classify partners by KMITL-specific partner type',
    'author': 'KMITL',
    'website': 'https://www.kmitl.ac.th',
    'category': 'KMITL',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/partner_type_data.xml',
        'views/res_partner_type_views.xml',
        'views/res_partner_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
}
