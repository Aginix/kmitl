# Copyright 2024 KMITL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Web Login ThaiD",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Aginix Technologies, KMITL",
    "summary": "ThaiD (Thailand Digital ID) login button for Odoo",
    "depends": ["auth_oidc", "auth_signup"],
    "data": [
        "views/auth_oauth_provider.xml",
        "data/auth_oauth_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "web_login_thaid/static/src/scss/login_thaid.scss",
        ],
    },
}
