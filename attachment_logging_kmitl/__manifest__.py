{
    "name": "Attachment Logging - KMITL Extensions",
    "summary": "Route many2many_binary widget deletes through the mail delete "
    "endpoint so attachment_logging fires and files are actually removed",
    "version": "16.0.1.0.0",
    "author": "KMITL",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden/Tools",
    "depends": ["attachment_logging"],
    "assets": {
        "web.assets_backend": [
            "attachment_logging_kmitl/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
