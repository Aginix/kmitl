/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ApprovalQueue } from "@disbursement/approval_queue/approval_queue";

// DR_FIELDS in the base queue is module-private, so we fetch attachment_count
// as a second, targeted read and merge the count onto each already-loaded
// request. Cheap: same ids we just searched, one extra roundtrip per refresh.
patch(ApprovalQueue.prototype, "disbursement_attachment_viewer", {
    async loadRequests() {
        await this._super(...arguments);
        const ids = this.state.requests.map((dr) => dr.id);
        if (!ids.length) {
            return;
        }
        const counts = await this.orm.read(
            "disbursement.request",
            ids,
            ["attachment_count"],
        );
        const countById = Object.fromEntries(
            counts.map((row) => [row.id, row.attachment_count]),
        );
        for (const dr of this.state.requests) {
            dr.attachment_count = countById[dr.id] || 0;
        }
    },
});
