/** @odoo-module **/

import { Component } from "@odoo/owl";
import { ControlPanel } from "@web/search/control_panel/control_panel";

export class Budget_control_panel extends Component {

    setup() {
        this.controlPanelDisplay = {
            "top-right": false,
            "bottom-right": false,
        };
    }
}

Budget_control_panel.template = "budget_plan_ui.budget_control_panel";
Budget_control_panel.components = { ControlPanel }
