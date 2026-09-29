/** @odoo-module **/

import {isPreviewable} from "@agx_photoviewer/js/photoviewer";
import {registerPatch} from "@mail/model/model_core";

// Make the chatter show the zoom cursor on every file the viewer can render.
registerPatch({
    name: "Attachment",
    fields: {
        isViewable: {
            compute() {
                return (
                    this._super() ||
                    isPreviewable({
                        name: this.displayName,
                        mimetype: this.mimetype,
                    })
                );
            },
        },
    },
});
