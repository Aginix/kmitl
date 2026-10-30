{
    "name": "Related Documents",
    "summary": "Cite in-system or out-of-system documents on a record as "
    "supporting evidence",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/related_document_kind_views.xml",
        "views/related_document_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_related_document/static/src/**/*",
        ],
    },
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
