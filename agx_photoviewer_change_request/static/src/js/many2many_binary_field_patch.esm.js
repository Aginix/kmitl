/** @odoo-module **/

import {useExternalListener, useState} from "@odoo/owl";
import {CHANGED_EVENT} from "@agx_change_request/js/change_request_panel.esm";
import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {patch} from "@web/core/utils/patch";

// Fetch the outstanding Change requests count of each attachment for the badge.
Many2ManyBinaryField.fieldsToFetch = {
    ...Many2ManyBinaryField.fieldsToFetch,
    outstanding_request_count: {name: "outstanding_request_count", type: "integer"},
};

patch(Many2ManyBinaryField.prototype, "agx_photoviewer_change_request", {
    setup() {
        this._super(...arguments);
        // Counts read again after a step taken here or by someone else.
        this.requestCounts = useState({});
        useExternalListener(window, CHANGED_EVENT, () => this.loadRequestCounts());
    },

    async loadRequestCounts() {
        const ids = this.files.map((file) => file.id).filter(Boolean);
        if (!ids.length) {
            return;
        }
        const counts = await this.orm.read("ir.attachment", ids, [
            "outstanding_request_count",
        ]);
        for (const {id, outstanding_request_count} of counts) {
            this.requestCounts[id] = outstanding_request_count;
        }
    },

    requestCount(file) {
        return file.id in this.requestCounts
            ? this.requestCounts[file.id]
            : file.outstanding_request_count;
    },
});
