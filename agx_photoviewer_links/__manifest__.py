{
    "name": "Photo Viewer - Links",
    "summary": "Open YouTube, Google Drive, Odoo and web link attachments "
    "in the photo viewer",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden",
    "depends": ["agx_photoviewer", "web_attachment_link"],
    "assets": {
        "web.assets_backend": [
            "agx_photoviewer_links/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": True,
    "license": "AGPL-3",
}
