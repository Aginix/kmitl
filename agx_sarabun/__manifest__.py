# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun",
    "summary": "Electronic Correspondence Management System (สารบรรณอิเล็กทรอนิกส์)",
    "version": "16.0.5.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "mail",
        "hr",
        "thai_date_utils",
        "l10n_th_fonts",  # Thai font rendering for the cover-sheet PDF (P5)
        "hr_employee_academic_standing_thailand",  # academic_standing_title (signature block)
        "hr_employee_digitized_signature",  # hr.employee.signature image (signature block)
    ],
    "data": [
        # Security
        "security/security.xml",
        "security/ir.model.access.csv",
        # Master data
        "data/sarabun_activity_data.xml",
        "data/sarabun_document_type.xml",
        # Reports
        "report/paperformat.xml",
        "report/report_cover_sheet.xml",
        # Wizards
        "wizard/sarabun_step_act_wizard_views.xml",
        # Views
        "views/sarabun_document_type_views.xml",
        "views/sarabun_position_views.xml",
        "views/sarabun_route_template_views.xml",
        "views/sarabun_sequence_views.xml",
        "views/sarabun_document_views.xml",
        "views/sarabun_menus.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
