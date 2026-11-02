/** @odoo-module **/
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import {ListRenderer} from "@web/views/list/list_renderer";
import {patch} from "@web/core/utils/patch";

patch(ListRenderer.prototype, "disbursement_partner_bank", {
    /**
     * Odoo refuses a row button on a line not saved yet ("click save first").
     * The payee bank wizard only needs the request and the payee, so open it
     * from the request instead: the form's button flow saves the request
     * (new line included) before running it.
     */
    onPayeeBankVirtualRowClick(record, button) {
        const partner = record.data.partner_id;
        if (button.clickParams.name !== "action_open_partner_bank_wizard" || !partner) {
            return this.displaySaveNotification();
        }
        const root = record.model.root;
        return this.env.onClickViewButton({
            clickParams: button.clickParams,
            getResParams: () => ({
                resModel: root.resModel,
                resId: root.resId,
                resIds: [root.resId],
                context: {...root.context, payee_bank_partner_ids: [partner[0]]},
                evalContext: root.evalContext,
            }),
        });
    },
});
