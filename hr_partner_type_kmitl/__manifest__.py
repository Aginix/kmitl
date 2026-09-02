# -*- coding: utf-8 -*-
{
    'name': 'HR ↔ Partner Type (KMITL)',
    'version': '16.0.1.0.0',
    'summary': "Classify an employee's work contact as internal-staff partner type",
    'author': 'KMITL',
    'website': 'https://www.kmitl.ac.th',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': ['hr', 'base_automation', 'partner_type_kmitl'],
    'data': ['data/base_automation.xml'],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
}
