/** @odoo-module **/

import {ChangeRequestPanel} from "@agx_change_request/js/change_request_panel.esm";
import {focusOnOpen} from "./annotation_change_request.esm";
import {openPhotoViewer} from "@agx_photoviewer/js/photoviewer";
import {patch} from "@web/core/utils/patch";

patch(ChangeRequestPanel.prototype, "agx_photoviewer_change_request", {
    /**
     * Open the file of a pinned request in the photo viewer, on its pin.
     */
    showPin(request) {
        const {pin} = request;
        const attachment = {
            id: pin.attachment_id,
            name: pin.file_name,
            mimetype: pin.mimetype,
        };
        focusOnOpen(pin.attachment_id, pin.annotation_id);
        openPhotoViewer([attachment], attachment);
    },
});
