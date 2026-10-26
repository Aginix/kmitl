/** @odoo-module **/

import {useExternalListener} from "@odoo/owl";
import {FormController} from "@web/views/form/form_controller";
import {REVISED_EVENT} from "./annotation_revision.esm";
import {patch} from "@web/core/utils/patch";
import {registry} from "@web/core/registry";

// The chatter shows the superseded revision as such and lists the new one.
registry.category("services").add("agx_photoviewer_annotation_revision", {
    dependencies: ["messaging"],
    start(env, {messaging}) {
        window.addEventListener(REVISED_EVENT, async (ev) => {
            const {previous_id, number, res_model, res_id} = ev.detail;
            const models = (await messaging.get()).models;
            models.Attachment.insert({id: previous_id, revisionSupersededBy: number});
            const thread = models.Thread.findFromIdentifyingData({
                id: res_id,
                model: res_model,
            });
            if (thread) {
                thread.fetchData(["attachments", "messages"]);
            }
        });
    },
});

// The form holding the file shows the new revision in its file fields.
patch(FormController.prototype, "agx_photoviewer_annotation_revision", {
    setup() {
        this._super(...arguments);
        useExternalListener(window, REVISED_EVENT, async (ev) => {
            const root = this.model.root;
            if (
                ev.detail.res_model === root.resModel &&
                ev.detail.res_id === root.resId &&
                !root.isDirty
            ) {
                await root.load();
                this.model.notify();
            }
        });
    },
});
