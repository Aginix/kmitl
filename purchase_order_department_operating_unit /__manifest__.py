# -*- coding: utf-8 -*-
{
    'name': 'Purchase_order_department_operating_unit ',
    'version': '16.0.1.0.0',
    'summary': """ Purchase_order_department_operating_unit  Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_order_department', 'purchase_operating_unit'],
    "data": [
        "views/purchase_order_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'purchase_order_department_operating_unit /static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
