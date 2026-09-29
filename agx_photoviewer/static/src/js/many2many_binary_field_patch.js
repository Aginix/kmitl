/** @odoo-module **/

import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {isPreviewable, openPhotoViewer} from "@agx_photoviewer/js/photoviewer";
import {patch} from "@web/core/utils/patch";

patch(Many2ManyBinaryField.prototype, "agx_photoviewer.Many2ManyBinaryField", {
    isPreviewable(file) {
        return isPreviewable(file);
    },

    onPreviewClick(ev, file) {
        // Buttons inside the wrapper (e.g. other modules' badges) keep their action.
        if (this.isPreviewable(file) && !ev.target.closest('[role="button"]')) {
            // Also cancels the download / new tab of the wrapped links.
            ev.preventDefault();
            openPhotoViewer(this.files, file);
        }
    },
});
