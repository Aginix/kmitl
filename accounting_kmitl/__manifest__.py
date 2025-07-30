{
    'name': 'KMITL Accounting',
    'version': '16.0.1.0.0',
    'category': 'Accounting',
    'summary': 'KMITL specific accounting customizations',
    'description': """
KMITL Accounting Module
=======================

This module provides accounting customizations specific to
King Mongkut's Institute of Technology Ladkrabang (KMITL).

This is a blank addon ready for customization.
    """,
    'author': 'KMITL',
    'website': 'https://www.kmitl.ac.th',
    'depends': [
        'base',
        'account_usability',
        'base_tier_validation',
    ],
    'data': [
        'security/kmitl_accounting_groups.xml',
        'security/ir.model.access.csv',
        'data/tier_definition.xml',
        'views/account_move_views.xml',
        'templates/tier_validation_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
