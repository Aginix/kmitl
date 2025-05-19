/** @odoo-module **/

import {ActionMenus} from "@web/search/action_menus/action_menus";
import {Component} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {useService} from "@web/core/utils/hooks";
export class BudgetExpenditureReportControlPanel extends Component {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
    }
}

BudgetExpenditureReportControlPanel.template =
    "budget.BudgetExpenditureReportControlPanel";
BudgetExpenditureReportControlPanel.components = {
    ControlPanel,
    Dropdown,
    DropdownItem,
    ActionMenus,
};
BudgetExpenditureReportControlPanel.props = {
    budgetTemplates: Object,
    selectedBudgetTemplate: Object,
    changeBudgetTemplate: Function,
};
