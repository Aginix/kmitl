{
    "name": "e-Sarabun Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL/Correspondence",
    "summary": "Route e-Saraban awaiting-action work into the unified Todo inbox "
    "(ADR-0014): tag the native activity types and add per-source sound control",
    # Core only — NO mail_activity_todo_role_unit: sarabun activities are personal
    # (one per snapshot holder), never role-in-unit group Todos. The per-source
    # sound refinement SOFT-depends on mail_activity_todo_sound (guarded at
    # runtime), so this bridge installs and tags todo_category without it.
    "depends": [
        "agx_sarabun",
        "mail_activity_todo",
    ],
    "data": [
        "data/mail_activity_type_update.xml",
        "data/mail_activity_completed_data.xml",
        "views/res_users_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
