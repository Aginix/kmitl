/** @odoo-module **/

import {
    CHANGED_EVENT,
    ChangeRequestPanel,
    refreshChatter,
} from "./change_request_panel.esm";
import {useEffect, useExternalListener, useState} from "@odoo/owl";
import {FormController} from "@web/views/form/form_controller";
import {patch} from "@web/core/utils/patch";

// A button beside the action menu opens the Change requests side panel of
// records whose model takes them (change.request.mixin).
patch(FormController.prototype, "agx_change_request", {
    setup() {
        this._super(...arguments);
        this.changeRequests = useState({
            enabled: Boolean(
                this.props.fields && this.props.fields.change_request_count
            ),
            open: false,
            count: 0,
        });
        if (this.changeRequests.enabled) {
            useEffect(
                (resId) => {
                    this.loadChangeRequestCount(resId);
                },
                () => [this.model.root.resId]
            );
            useExternalListener(window, CHANGED_EVENT, () => {
                const resId = this.model.root.resId;
                this.loadChangeRequestCount(resId);
                if (resId && !this.changeRequests.open) {
                    refreshChatter(this.env, this.props.resModel, resId);
                }
            });
        }
    },

    async loadChangeRequestCount(resId) {
        this.changeRequests.count = resId
            ? await this.env.services.orm.call("change.request", "request_count", [
                  this.props.resModel,
                  resId,
              ])
            : 0;
    },

    toggleChangeRequests() {
        this.changeRequests.open = !this.changeRequests.open;
    },

    onChangeRequestsChanged(count) {
        this.changeRequests.count = count;
    },
});

Object.assign(FormController.components, {ChangeRequestPanel});
