{
    "name": "Photo Viewer - Annotation",
    "summary": "Tick, draw, highlight and comment on image and PDF attachments "
    "in the photo viewer",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden",
    "depends": ["agx_photoviewer", "mail", "l10n_th_fonts"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_photoviewer_annotation/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
