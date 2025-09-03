{
    'name': 'IFrame Viewer Widget',
    'version': '16.0.1.0.0',
    'category': 'Web',
    'summary': 'IFrame viewer widget for Odoo backend',
    'description': """
        This module adds an iframe_viewer widget that allows displaying URLs
        in an embedded iframe within Odoo backend forms and views.
        
        Usage:
        <field name="preview_url" widget="iframe_viewer" />
    """,
    'author': 'KMITL',
    'website': 'https://www.kmitl.ac.th',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'iframe_viewer_widget/static/src/js/iframe_viewer_widget.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}