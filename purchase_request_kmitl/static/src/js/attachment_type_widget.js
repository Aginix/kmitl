/** @odoo-module **/

import {registerAttachmentMetadataWidget} from "@web_attachment_metadata/components/attachment_metadata/attachment_metadata_field";

registerAttachmentMetadataWidget({
    widgetName: "many2many_binary_attachment_type",
    metadataType: "selection",
    metadataField: "attachment_type",
    metadataLabel: "Attachment Type",
    metadataSelection: [
        ["tor", "Specification (TOR)"],
        ["rfq", "Quotation"],
        ["etc", "Etc"],
    ],
});
