# -*- coding: utf-8 -*-
{
    "name": "Stock KMITL",
    "version": "16.0.1.0.0",
    "summary": "KMITL stock customizations: inventory adjustment defaults & access "
    "restriction, warehouse initialization, and scrap tracking fields",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "stock",
        "stock_inventory",
        "stock_operating_unit",
    ],
    "data": [
        "security/security.xml",
        "views/stock.xml",
        "views/stock_inventory_views.xml",
        "views/stock_scrap_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
}
