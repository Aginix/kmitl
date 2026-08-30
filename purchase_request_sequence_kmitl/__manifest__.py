# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Sequence KMITL',
    'version': '16.0.1.1.0',
    'summary': """ Purchase Request Sequence KMITL Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    # This module owns all sequence-related behaviour: XML sequence, the
    # _get_default_name no-op, the write() hook that mints the number on the
    # state transition out of draft, the fiscal_year_locked flag, and the FY
    # freeze guard. It depends on purchase_request_kmitl for
    # account_fiscal_year_id and the form view it inherits.
    'depends': [
        'purchase_request_kmitl',
        'l10n_th_base_sequence',
    ],
    'data': [
        'data/sequence.xml',
        'views/purchase_request_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
