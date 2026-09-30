# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Attachment Carousel",
    "version": "16.0.1.0.0",
    "category": "Extra Tools",
    "license": "AGPL-3",
    "author": "KMITL",
    "summary": (
        "Reusable OWL field widget that turns attachment_ids into a "
        "clickable in-app carousel, with LibreOffice preview for Office files"
    ),
    "depends": [
        "web",
    ],
    "assets": {
        "web.assets_backend": [
            "attachment_carousel/static/src/js/attachment_carousel_dialog.js",
            "attachment_carousel/static/src/js/attachment_carousel_field.js",
            "attachment_carousel/static/src/xml/attachment_carousel_dialog.xml",
            "attachment_carousel/static/src/xml/attachment_carousel_field.xml",
            "attachment_carousel/static/src/scss/attachment_carousel.scss",
        ],
    },
    "installable": True,
}
