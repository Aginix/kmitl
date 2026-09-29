# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Disbursement - Attachment Carousel",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "AGPL-3",
    "author": "KMITL",
    "summary": "In-app OWL carousel to preview all disbursement attachments",
    "depends": [
        "disbursement",
        "web",
    ],
    "data": [
        "views/disbursement_request_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "disbursement_attachment_carousel/static/src/js/attachment_carousel.js",
            "disbursement_attachment_carousel/static/src/xml/attachment_carousel.xml",
            "disbursement_attachment_carousel/static/src/scss/attachment_carousel.scss",
        ],
    },
    "installable": True,
}
