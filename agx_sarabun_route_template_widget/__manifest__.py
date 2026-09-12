# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun: Route Template Picker Widget",
    "summary": (
        "Visibility badge (ส่วนตัว / สังกัด / ทุกคน) inside the "
        "route_template_id dropdown on the document form"
    ),
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["agx_sarabun_user_template"],
    "data": [
        "views/sarabun_document_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_sarabun_route_template_widget/static/src/route_template_m2o/route_template_m2o.js",
            "agx_sarabun_route_template_widget/static/src/route_template_m2o/route_template_m2o.xml",
            "agx_sarabun_route_template_widget/static/src/route_template_m2o/route_template_m2o.scss",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
