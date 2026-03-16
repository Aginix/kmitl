# -*- coding: utf-8 -*-
{
    "name": "HR Recruitment KMITL",
    "version": "16.0.1.0.0",
    "summary": "Custom theme and pages for KMITL recruitment website",
    "author": "KMITL",
    "category": "Website",
    "depends": [
        "website",
        "website_hr_recruitment",
        "theme_kmitl",
        "base_location",
        "partner_firstname",
        "partner_middlename",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/website_data.xml",
        "views/website_hr_recruitment_templates.xml",
        "views/snippets/s_benefit_card.xml",
        "views/snippets/snippets.xml",
        "views/website_templates.xml",
        "views/portal_profile_views.xml",
        "views/res_partner_views.xml",
        "views/profile_templates.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "hr_recruitment_kmitl/static/src/scss/theme.scss",
        ],
        "web._assets_frontend_helpers": [
            (
                "prepend",
                "hr_recruitment_kmitl/static/src/scss/bootstrap_overridden.scss",
            ),
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
