{
    "name": "Purchase Work Acceptance Digital Signature",
    "version": "16.0.1.0.0",
    "summary": "Snapshot committee + procurement officer signatures into Work Acceptance "
    "documents at approval time, and render them in the PDF report.",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "digital_signature_kmitl",
        "purchase_work_acceptance_kmitl",
    ],
    "data": [
        "reports/report_work_acceptance.xml",
        "reports/report_committee_acceptance.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
