# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Student List Import",
    "summary": "Add many students to a disbursement request from one Excel list "
    "(scholarships, teaching-assistant pay)",
    "version": "16.0.1.0.1",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement", "partner_student_kmitl"],
    "external_dependencies": {"python": ["xlrd", "xlsxwriter"]},
    "data": [
        "security/ir.model.access.csv",
        "wizards/disbursement_student_import_views.xml",
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
