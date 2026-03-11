# -*- coding: utf-8 -*-
{
    "name": "Fiscal Year Systray",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Production/Stable",
    "category": "Accounting",
    "depends": ["account_fiscal_year_enhance"],
    "assets": {
        "web.assets_backend": [
            "web_fiscal_year_systray/static/src/js/fiscal_year_systray.esm.js",
            "web_fiscal_year_systray/static/src/xml/fiscal_year_systray.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
