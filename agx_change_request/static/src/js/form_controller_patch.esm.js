/** @odoo-module **/

import {
    CHANGED_EVENT,
    ChangeRequestPanel,
    refreshChatter,
} from "./change_request_panel.esm";
import {onWillUnmount, useEffect, useExternalListener, useState} from "@odoo/owl";
import {FormController} from "@web/views/form/form_controller";
import {patch} from "@web/core/utils/patch";

// Notification the server sends on the record's bus channel after each step.
const CHANGED_NOTIFICATION = "agx_change_request/changed";

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
            const bus = this.env.services.bus_service;
            // Live: a step taken by anyone on this record, in another form
            // or tab, refreshes the button, the panel and the chatter here.
            useEffect(
                (resId) => {
                    this.loadChangeRequestCount(resId);
                    if (!resId) {
                        return;
                    }
                    const channel = `agx_change_request:${this.props.resModel}:${resId}`;
                    bus.addChannel(channel);
                    return () => bus.deleteChannel(channel);
                },
                () => [this.model.root.resId]
            );
            const onNotification = ({detail: notifications}) => {
                const root = this.model.root;
                const changed = notifications.some(
                    ({type, payload}) =>
                        type === CHANGED_NOTIFICATION &&
                        payload.res_model === root.resModel &&
                        payload.res_id === root.resId
                );
                if (changed) {
                    window.dispatchEvent(new CustomEvent(CHANGED_EVENT));
                }
            };
            bus.addEventListener("notification", onNotification);
            onWillUnmount(() =>
                bus.removeEventListener("notification", onNotification)
            );
            useExternalListener(window, CHANGED_EVENT, () => {
                const resId = this.model.root.resId;
                this.loadChangeRequestCount(resId);
                if (resId) {
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
