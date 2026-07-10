/** @odoo-module **/

import {registerAttachmentClassifierWidget} from "@web_attachment_classifier/components/attachment_classifier/attachment_classifier_field";

registerAttachmentClassifierWidget({
    widgetName: "many2many_binary_doctype",
    classifierField: "document_type_id",
    classifierModel: "kris.project.document.type",
    classifierLabel: "Document Type",
    classifierRequired: true,
});
