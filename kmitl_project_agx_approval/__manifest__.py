# -*- coding: utf-8 -*-
{
    "name": "KMITL Project — Approval Request Budget Draw",
    "summary": "Draw an approval request's budget from a KMITL project's reserved slip",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "LGPL-3",
    "depends": [
        "agx_approval",
        "kmitl_project",
    ],
    "data": [],
    "application": False,
    "installable": True,
    # Glue module: activate automatically whenever both sides are present, so a
    # project-funded expense can always be raised through the expense module
    # once projects and budget-aware approval requests coexist.
    "auto_install": True,
}
