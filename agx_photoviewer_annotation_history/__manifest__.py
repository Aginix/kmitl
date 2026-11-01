{
    "name": "Photo Viewer - Annotation History",
    "summary": "Browse the changes made to the annotations of a file and see "
    "each one drawn on the page",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden",
    "depends": ["agx_photoviewer_annotation"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_photoviewer_annotation_history/static/src/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
