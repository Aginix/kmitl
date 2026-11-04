{
    "name": "e-Sarabun: Document Type Readers",
    "summary": "Read-only access to every หนังสือ of a type within the reader's "
    "Operating Units, without being on the Route (ADR-0021)",
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "agx_sarabun_operating_unit",
    ],
    "data": [
        "security/security.xml",
        "views/sarabun_document_type_views.xml",
        "views/sarabun_document_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
