{
    "name": "e-Sarabun: Correct Signed Capacity",
    "summary": "Route editor corrects the ตำแหน่ง a บุคลากร step was signed in, even "
    "after completion (ADR-0019)",
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "agx_sarabun_route_edit",
        "agx_sarabun_person_capacity",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/sarabun_signed_capacity_wizard_views.xml",
        "views/sarabun_document_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
