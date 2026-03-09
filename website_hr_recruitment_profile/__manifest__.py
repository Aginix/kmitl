{
    "name": "Website HR Recruitment Profile",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "category": "Human Resources/Recruitment",
    "summary": "Auto-populate job applications from portal profile",
    "depends": ["website_hr_recruitment", "portal_profile"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_applicant_views.xml",
        "views/website_templates.xml",
    ],
    "assets": {
        "website.assets_editor": [
            "website_hr_recruitment_profile/static/src/js/form_editor.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
