{
    "name": "Account Asset Batch Viewer",
    "version": "16.0.1.0.0",
    "summary": "Grant purchase viewer read-only access to asset batch models",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "account_asset_batch",
        "account_asset_subcomponent_kmitl",
        "purchase_viewer",
    ],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
