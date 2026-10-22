# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "MIS Builder Hierarchy",
    "version": "16.0.1.0.0",
    "category": "Reporting",
    "summary": "Auto-expand hierarchical source data (parent_id) in MIS Builder reports",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "AGPL-3",
    "maintainers": ["n3n"],
    "development_status": "Beta",
    "depends": [
        "mis_builder",
    ],
    "data": [
        "views/mis_report_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mis_builder_hierarchy/static/src/components/mis_report_widget_hierarchy.esm.js",
            "mis_builder_hierarchy/static/src/components/mis_report_widget_hierarchy.xml",
            "mis_builder_hierarchy/static/src/components/mis_report_widget_hierarchy.css",
        ],
    },
    "installable": True,
    "application": False,
}
