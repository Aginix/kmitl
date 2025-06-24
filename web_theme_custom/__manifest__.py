# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Web Theme Custom",
    "category": "Hidden",
    "version": "1.0",
    "description": """
Odoo Enterprise Web Client.
===========================

This module modifies the web addon to provide Enterprise design and responsiveness.
        """,
    "depends": ["web"],
    "auto_install": True,
    "data": [
        "views/webclient_templates.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            (
                "after",
                "web/static/src/scss/primary_variables.scss",
                "web_theme_custom/static/src/**/**/*.variables.scss",
            ),
            (
                "before",
                "web/static/src/scss/primary_variables.scss",
                "web_theme_custom/static/src/scss/primary_variables.scss",
            ),
        ],
        "web._assets_secondary_variables": [
            (
                "before",
                "web/static/src/scss/secondary_variables.scss",
                "web_theme_custom/static/src/scss/secondary_variables.scss",
            ),
        ],
        "web._assets_backend_helpers": [
            (
                "before",
                "web/static/src/scss/bootstrap_overridden.scss",
                "web_theme_custom/static/src/scss/bootstrap_overridden.scss",
            ),
        ],
        "web.assets_common": [
            "web_theme_custom/static/src/webclient/home_menu/home_menu_background.scss",
            "web_theme_custom/static/src/webclient/navbar/navbar.scss",
        ],
        "web.assets_frontend": [
            "web_theme_custom/static/src/webclient/home_menu/home_menu_background.scss",
            "web_theme_custom/static/src/webclient/navbar/navbar.scss",
        ],
        "web.assets_backend": [
            (
                "replace",
                "web/static/src/legacy/scss/fields_extra.scss",
                "web_theme_custom/static/src/legacy/scss/fields.scss",
            ),
            (
                "replace",
                "web/static/src/legacy/scss/form_view_extra.scss",
                "web_theme_custom/static/src/legacy/scss/form_view.scss",
            ),
            (
                "replace",
                "web/static/src/legacy/scss/list_view_extra.scss",
                "web_theme_custom/static/src/legacy/scss/list_view.scss",
            ),
            "web_theme_custom/static/src/legacy/scss/dropdown.scss",
            "web_theme_custom/static/src/legacy/scss/control_panel_mobile.scss",
            "web_theme_custom/static/src/legacy/scss/kanban_view.scss",
            "web_theme_custom/static/src/legacy/scss/touch_device.scss",
            "web_theme_custom/static/src/legacy/scss/form_view_mobile.scss",
            "web_theme_custom/static/src/legacy/scss/modal_mobile.scss",
            "web_theme_custom/static/src/webclient/**/*.scss",
            (
                "remove",
                "web_theme_custom/static/src/webclient/home_menu/home_menu_background.scss",
            ),
            ("remove", "web_theme_custom/static/src/webclient/navbar/navbar.scss"),
            "web_theme_custom/static/src/views/**/*.scss",
        ],
    },
    "license": "OEEL-1",
}
