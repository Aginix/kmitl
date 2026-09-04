# -*- coding: utf-8 -*-
{
    "name": "Advance Payment Followup",
    "version": "16.0.1.0.0",
    "summary": """ ติดตามลูกหนี้เงินยืม: countdown, หน้าติดตาม, digest รายสัปดาห์ """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["advance_payment"],
    "data": [
        "data/ir_cron_data.xml",
        "data/mail_template_data.xml",
        "views/advance_payment_followup_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
