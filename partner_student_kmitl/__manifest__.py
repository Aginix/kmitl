# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "KMITL Student Contacts",
    "summary": "Student ID on contacts, named from the KMITL student catalog API",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": ["base_setup", "partner_type_kmitl"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
