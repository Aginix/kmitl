# -*- coding: utf-8 -*-
{
    "name": "Partner Rich Autocomplete",
    "version": "16.0.1.0.0",
    "summary": "Rich multi-line dropdown widget for res.partner Many2one fields",
    "category": "Tools",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "AGPL-3",
    "depends": ["web"],
    "data": [
        "views/res_partner_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_partner_autocomplete/static/src/partner_m2o/partner_m2o.js",
            "agx_partner_autocomplete/static/src/partner_m2o/partner_m2o.xml",
            "agx_partner_autocomplete/static/src/partner_m2o/partner_m2o.scss",
        ],
    },
    "installable": True,
}
