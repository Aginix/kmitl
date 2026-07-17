{
    "name": "Web Attachment Classifier",
    "summary": "Drag & drop + document-type classification for the standard "
    "many2many_binary attachment widget",
    "version": "16.0.2.0.2",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden",
    "depends": ["web", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/ir_attachment_document_type_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "web_attachment_classifier/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
