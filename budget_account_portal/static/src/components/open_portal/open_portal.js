/** @odoo-module **/

import {ListController} from "@web/views/list/list_controller";
import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class BudgetAccountListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }
    async onOpenPortal() {
        const url = "/budget/budget_account";
        window.open(url, "_blank").focus();
    }
}

registry.category("views").add("budget_account_tree", {
    ...listView,
    Controller: BudgetAccountListController,
    buttonTemplate: "BudgetAccountListView.open_portal_button",
});
