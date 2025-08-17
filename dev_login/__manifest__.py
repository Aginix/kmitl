{
    'name': 'Developer Login',
    'version': '16.0.1.0.0',
    'category': 'Development',
    'summary': 'Quick admin login button for development environment',
    'description': """
Developer Login
===============

Adds a "Login as admin" button to the login page for development convenience.

Features:
- One-click admin login for development
- Only enabled in development mode
- Security restrictions to prevent production use

Warning: This module should NEVER be installed in production environments.
    """,
    'author': 'KMITL',
    'website': 'https://www.kmitl.ac.th',
    'depends': ['base', 'web'],
    'data': [
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'dev_login/static/src/js/dev_login.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'development_status': 'Beta',
    'license': 'LGPL-3',
}