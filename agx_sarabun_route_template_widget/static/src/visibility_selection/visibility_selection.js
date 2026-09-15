/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectionField } from "@web/views/fields/selection/selection_field";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

// Hide 'public' from the visibility Selection dropdown for non-manager users.
// Filtering here (client-side, per-widget) rather than via a fields_get
// override keeps the model's full selection intact — so the badge/label
// widgets on trees and Search-More dialogs can still map stored 'public'
// values to their label. The server-side @api.constrains in
// agx_sarabun_user_template remains the enforcement; this is UI polish.

// Register the class directly — Odoo 16.0 does not yet expose the
// `selectionField` object wrapper (that pattern lands in a later version),
// so `registry.add("...", { ...selectionField, component: ... })` produces
// an object Odoo cannot `new()` at Field render time ("C is not a
// constructor" in owl's ComponentNode). Matches the class-registration
// pattern used by the other widgets in this repo (agx_partner_autocomplete
// etc.).
export class SarabunVisibilitySelectionField extends SelectionField {
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

registry
    .category("fields")
    .add("sarabun_visibility_selection", SarabunVisibilitySelectionField);
