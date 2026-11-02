{
    "name": "Change Requests",
    "summary": "Ask a record's maker to fix or explain something and follow it "
    "until its author closes it",
    "version": "16.0.1.1.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_activity_type_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_change_request/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
