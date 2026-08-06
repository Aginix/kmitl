/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";
import {attr} from "@mail/model/model_field";

// Extend mail's Attachment model with the document-type name that our
// override of ir.attachment._attachment_format ships in the payload.
// registerPatch is mail's own patch helper — it merges into the model
// registered by mail before it's finalised, so both fields and
// modelMethods are additive.
registerPatch({
    name: "Attachment",
    fields: {
        documentTypeName: attr(),
    },
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            if ("documentTypeName" in data) {
                data2.documentTypeName = data.documentTypeName;
            }
            return data2;
        },
    },
});
