/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

// The annotation count our ir.attachment._attachment_format adds to the payload.
registerPatch({
    name: "Attachment",
    fields: {
        annotationCount: attr({default: 0}),
    },
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            if ("annotationCount" in data) {
                data2.annotationCount = data.annotationCount;
            }
            return data2;
        },
    },
});
