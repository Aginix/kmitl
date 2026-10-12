{
    "name": "Photo Viewer - File Types",
    "summary": "Preview PDF, video, Word, Excel and PowerPoint attachments "
    "in the photo viewer",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden",
    "depends": ["agx_photoviewer"],
    "assets": {
        # The heavy libraries under static/lib are lazy-loaded on first use.
        "web.assets_backend": [
            "agx_photoviewer_filetypes/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
