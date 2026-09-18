{
    "name": "Budget Commitment Rich Picker",
    "version": "16.0.1.0.0",
    "summary": "Multi-line dropdown for picking a budget commitment (ใบจองงบประมาณ)",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "AGPL-3",
    "depends": [
        "budget",
    ],
    "assets": {
        "web.assets_backend": [
            "budget_commitment_autocomplete/static/src/commitment_m2o/budget_commitment_m2o.js",
            "budget_commitment_autocomplete/static/src/commitment_m2o/budget_commitment_m2o.xml",
            "budget_commitment_autocomplete/static/src/commitment_m2o/budget_commitment_m2o.scss",
        ],
    },
    "installable": True,
}
