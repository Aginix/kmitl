{
    "name": "Photo Viewer",
    "summary": "Preview image attachments in a draggable photo viewer "
    "(attachment fields and chatter)",
    "version": "16.0.1.0.1",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden",
    "depends": ["web", "mail"],
    "assets": {
        "web.assets_backend": [
            "agx_photoviewer/static/lib/photoviewer/photoviewer.min.css",
            "agx_photoviewer/static/lib/photoviewer/photoviewer.min.js",
            "agx_photoviewer/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
