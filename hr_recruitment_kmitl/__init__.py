from . import controllers
from . import models
from odoo import api, SUPERUSER_ID


def create_job_website_and_menu(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env.ref("hr_recruitment_kmitl.job_website")
    theme = env.ref("base.module_theme_kmitl")
    # theme.with_context(website_id=website.id).button_upgrade()
    theme._theme_load(website)
    website.menu_id.child_id.unlink()

    default_menu = website.menu_id.filtered(lambda m: m.url == "/default-main-menu")

    env["website.menu"].create(
        [
            {
                "name": "Home",
                "url": "/jobs",
                "website_id": website.id,
                "parent_id": default_menu.id,
                "sequence": 10,
            },
            {
                "name": "Jobs",
                "url": "/jobs",
                "website_id": website.id,
                "parent_id": default_menu.id,
                "sequence": 20,
            },
            {
                "name": "My Applications",
                "url": "/my/applications",
                "website_id": website.id,
                "parent_id": default_menu.id,
                "sequence": 30,
            },
            {
                "name": "Onboarding",
                "url": "/my/onboarding",
                "website_id": website.id,
                "parent_id": default_menu.id,
                "sequence": 40,
            },
            {
                "name": "Profile",
                "url": "/my/profile",
                "website_id": website.id,
                "parent_id": default_menu.id,
                "sequence": 50,
            },
        ]
    )
