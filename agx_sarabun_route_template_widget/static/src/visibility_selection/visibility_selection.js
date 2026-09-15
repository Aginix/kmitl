/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    SelectionField,
    selectionField,
} from "@web/views/fields/selection/selection_field";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

// Hide 'public' from the visibility Selection dropdown for non-manager users.
// Filtering here (client-side, per-widget) rather than via a fields_get
// override keeps the model's full selection intact — so the badge/label
// widgets on trees and Search-More dialogs can still map stored 'public'
// values to their label. The server-side @api.constrains in
// agx_sarabun_user_template remains the enforcement; this is UI polish.

class SarabunVisibilitySelectionField extends SelectionField {
    setup() {
        super.setup();
        this.userService = useService("user");
        this.state = useState({ isManager: true });
        onWillStart(async () => {
            this.state.isManager = await this.userService.hasGroup(
                "agx_sarabun.group_sarabun_manager"
            );
        });
    }

    get options() {
        const opts = super.options;
        if (this.state.isManager) {
            return opts;
        }
        return opts.filter((opt) => opt[0] !== "public");
    }
}

export const sarabunVisibilitySelectionField = {
    ...selectionField,
    component: SarabunVisibilitySelectionField,
};

registry
    .category("fields")
    .add("sarabun_visibility_selection", sarabunVisibilitySelectionField);
