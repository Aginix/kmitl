/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

// The open Change requests count our ir.attachment._attachment_format adds.
registerPatch({
    name: "Attachment",
    fields: {
        openRequestCount: attr({default: 0}),
    },
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            if ("openRequestCount" in data) {
                data2.openRequestCount = data.openRequestCount;
            }
            return data2;
        },
    },
});
