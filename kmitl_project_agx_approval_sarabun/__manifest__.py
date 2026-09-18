# -*- coding: utf-8 -*-
{
    "name": "KMITL Project — Approval Request e-Saraban Skip",
    "summary": "Auto-approve a project-funded approval request, skipping e-Saraban",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "LGPL-3",
    "depends": [
        "kmitl_project_agx_approval",
        "agx_approval_sarabun",
    ],
    "data": [],
    "application": False,
    "installable": True,
    # Glue module: activate automatically whenever both sides are present, so a
    # project-funded expense always skips e-Saraban once the two apps coexist.
    "auto_install": True,
}
