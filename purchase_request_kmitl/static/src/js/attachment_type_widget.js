/** @odoo-module **/

import {registerAttachmentClassifierWidget} from "@web_attachment_classifier/components/attachment_classifier/attachment_classifier_field";

registerAttachmentClassifierWidget({
    widgetName: "many2many_binary_attachment_type",
    classifierType: "selection",
    classifierField: "attachment_type",
    classifierLabel: "Attachment Type",
    classifierSelection: [
        ["tor", "Specification (TOR)"],
        ["rfq", "Quotation"],
        ["etc", "Etc"],
    ],
    classifierRequired: true,
});
