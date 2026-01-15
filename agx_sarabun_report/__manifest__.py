# -*- coding: utf-8 -*-
{
    'name': 'Agx Sarabun Report',
    'version': '16.0.1.0.0',
    'summary': """ Agx Sarabun Report Summary """,
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': [
        "agx_sarabun",
        "l10n_th_amount_to_text",
        "l10n_th_fonts",
        "thai_date_utils",
    ],
    'data': [
        "report/paperformat.xml",
        "report/report_sarabun.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'agx_sarabun_report/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
