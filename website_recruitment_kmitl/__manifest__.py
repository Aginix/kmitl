# -*- coding: utf-8 -*-
{
    "name": "Website Recruitment KMITL",
    "version": "16.0.1.0.0",
    "summary": "Custom theme and pages for KMITL recruitment website",
    "author": "KMITL",
    "category": "Website",
    "depends": ["website", "website_hr_recruitment"],
    "data": [
        "data/website_data.xml",
        "views/website_hr_recruitment_templates.xml",
        "views/snippets/s_benefit_card.xml",
        "views/snippets/snippets.xml",
        "views/website_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_recruitment_kmitl/static/src/scss/theme.scss",
        ],
        "web._assets_frontend_helpers": [
            (
                "prepend",
                "website_recruitment_kmitl/static/src/scss/bootstrap_overridden.scss",
            ),
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
