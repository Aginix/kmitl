# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun: Standard Comments",
    "summary": "Reusable ข้อความมาตรฐาน (canned เกษียน text) for the Act-on-step wizard",
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "agx_sarabun",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sarabun_standard_comment_views.xml",
        "views/sarabun_verb_views.xml",
        "wizard/sarabun_step_act_wizard_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
