# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun: Person-Mode Capacity Label",
    "summary": "Pick a signing capacity (ตำแหน่ง) when targeting a specific person"
    " (บุคลากร) on a Routing Step / Route Template / Act wizard — a UX convenience"
    " for name-first lookup when the user knows the person but not the title.",
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "agx_sarabun",
    ],
    "data": [
        "views/sarabun_document_views.xml",
        "views/sarabun_route_template_views.xml",
        "wizard/sarabun_step_act_wizard_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
