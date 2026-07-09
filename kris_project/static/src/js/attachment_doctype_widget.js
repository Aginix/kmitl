/** @odoo-module **/

import {registerAttachmentMetadataWidget} from "@web_attachment_metadata/components/attachment_metadata/attachment_metadata_field";

registerAttachmentMetadataWidget({
    widgetName: "many2many_binary_doctype",
    metadataField: "document_type_id",
    metadataModel: "kris.project.document.type",
    metadataLabel: "Document Type",
});
