# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun",
    "summary": "Electronic Correspondence Management System (สารบรรณอิเล็กทรอนิกส์)",
    "version": "16.0.6.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "mail",
        "hr",
        "thai_date_utils",
        "l10n_th_fonts",  # Thai font rendering for the cover-sheet PDF (P5)
        "hr_employee_digitized_signature",  # hr.employee.signature image (signature block)
        # academic prefix (hr_employee_academic_standing_thailand / academic_standing_title)
        # is deferred to a later phase — see report/sarabun_reports.xml.
    ],
    "data": [
        # Security
        "security/security.xml",
        "security/ir.model.access.csv",
        # Master data
        "data/sarabun_activity_data.xml",
        "data/sarabun_verb_data.xml",
        "data/sarabun_addressee_prefix_data.xml",
        "data/sarabun_document_type.xml",
        # Reports
        "report/paperformat.xml",
        "report/sarabun_reports.xml",
        # Wizards
        "wizard/sarabun_step_act_wizard_views.xml",
        "wizard/sarabun_recall_wizard_views.xml",
        "wizard/sarabun_send_wizard_views.xml",
        # Views
        "views/sarabun_document_type_views.xml",
        "views/sarabun_position_views.xml",
        "views/sarabun_department_views.xml",
        "views/sarabun_verb_views.xml",
        "views/sarabun_addressee_prefix_views.xml",
        "views/sarabun_route_template_views.xml",
        "views/sarabun_sequence_views.xml",
        "views/sarabun_document_views.xml",
        "views/sarabun_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_sarabun/static/src/scss/sarabun_form.scss",
            "agx_sarabun/static/src/js/sarabun_document_form.esm.js",
            "agx_sarabun/static/src/js/sarabun_pdf_preview.esm.js",
            "agx_sarabun/static/src/xml/sarabun_pdf_preview.xml",
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
