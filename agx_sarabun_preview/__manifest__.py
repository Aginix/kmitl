# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun — Routing Timeline Preview",
    "summary": "Visual routing-timeline preview for e-Sarabun documents",
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["agx_sarabun"],
    "data": [
        "views/sarabun_document_views.xml",
        "views/sarabun_send_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_sarabun_preview/static/src/scss/sarabun_routing_timeline.scss",
            "agx_sarabun_preview/static/src/js/sarabun_routing_timeline.esm.js",
            "agx_sarabun_preview/static/src/xml/sarabun_routing_timeline.xml",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
