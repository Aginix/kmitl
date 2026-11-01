/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

// The latest revision number our ir.attachment._attachment_format adds to a
// superseded revision: a chatter message keeps it, marked as superseded.
registerPatch({
    name: "Attachment",
    fields: {
        revisionSupersededBy: attr({default: 0}),
    },
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            if ("revisionSupersededBy" in data) {
                data2.revisionSupersededBy = data.revisionSupersededBy;
            }
            return data2;
        },
    },
});

// The record's files, counted on the chatter, are the latest revisions only.
// Superseded ones still come from the server, flagged: leaving them out there
// would delete them from the client store (originThreadAttachments is
// causal), and so from the messages that hold them.
registerPatch({
    name: "Thread",
    fields: {
        allAttachments: {
            compute() {
                return this._super().filter(
                    (attachment) => !attachment.revisionSupersededBy
                );
            },
        },
    },
});
