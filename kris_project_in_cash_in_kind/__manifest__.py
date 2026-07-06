# -*- coding: utf-8 -*-
{
    "name": "KRIS Project — In Cash / In Kind",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "summary": "แยกมูลค่าโครงการงานวิจัยเป็นทุนเงินสด (In Cash) และทุนสิ่งของ (In Kind)",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kris_project",
    ],
    "data": [
        "views/kris_project_views.xml",
    ],
    "demo": [
        "data/kris_project_demo.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
