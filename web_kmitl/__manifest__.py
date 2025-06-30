# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Web KMITL",
    "category": "KMITL",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "description": """
Odoo KMITL Web Client.
===========================

This module modifies the web addon to provide KMITL design and responsiveness.
        """,
    "depends": ["web"],
    "auto_install": False,
    "data": [],
    "assets": {
        "web._assets_primary_variables": [
            (
                "after",
                "web/static/src/scss/primary_variables.scss",
                "web_kmitl/static/src/**/**/*.variables.scss",
            ),
            (
                "before",
                "web/static/src/scss/primary_variables.scss",
                "web_kmitl/static/src/scss/primary_variables.scss",
            ),
        ],
        "web._assets_secondary_variables": [
            (
                "before",
                "web/static/src/scss/secondary_variables.scss",
                "web_kmitl/static/src/scss/secondary_variables.scss",
            ),
        ],
        "web._assets_backend_helpers": [
            (
                "before",
                "web/static/src/scss/bootstrap_overridden.scss",
                "web_kmitl/static/src/scss/bootstrap_overridden.scss",
            ),
        ],
        "web.assets_backend": [
            (
                "replace",
                "web/static/src/legacy/scss/fields_extra.scss",
                "web_kmitl/static/src/legacy/scss/fields.scss",
            ),
            (
                "replace",
                "web/static/src/legacy/scss/form_view_extra.scss",
                "web_kmitl/static/src/legacy/scss/form_view.scss",
            ),
            (
                "replace",
                "web/static/src/legacy/scss/list_view_extra.scss",
                "web_kmitl/static/src/legacy/scss/list_view.scss",
            ),
            "web_kmitl/static/src/legacy/scss/dropdown.scss",
            "web_kmitl/static/src/legacy/scss/control_panel_mobile.scss",
            "web_kmitl/static/src/legacy/scss/kanban_view.scss",
            "web_kmitl/static/src/legacy/scss/touch_device.scss",
            "web_kmitl/static/src/legacy/scss/form_view_mobile.scss",
            "web_kmitl/static/src/legacy/scss/modal_mobile.scss",
            "web_kmitl/static/src/views/**/*.scss",
        ],
    },
    "license": "OEEL-1",
}
