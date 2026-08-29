/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

// SelectCreateDialog hardcodes display.searchPanel to false for every picker.
// The partner_autocomplete "Search More…" dialog wants a real searchpanel, so
// this patch flips it on, but only when the caller opts in via the
// agx_partner_ac_searchpanel context flag — every other Search More dialog in
// the app stays untouched.
patch(SelectCreateDialog.prototype, "agx_partner_autocomplete.SelectCreateDialog", {
    setup() {
        this._super(...arguments);
        if (this.props.context && this.props.context.agx_partner_ac_searchpanel) {
            this.baseViewProps.display = { ...this.baseViewProps.display, searchPanel: true };
        }
    },
});
