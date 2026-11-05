{
    "name": "e-Sarabun: Operating Unit",
    "summary": "Operating Unit on หนังสือ — taken from the origin record, else the "
    "creator's default OU (ADR-0021)",
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "agx_sarabun",
        "operating_unit",
    ],
    "data": [
        "views/sarabun_document_views.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
