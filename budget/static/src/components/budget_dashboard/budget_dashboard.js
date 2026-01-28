/** @odoo-module */

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class BudgetDashboard extends Component {
    static template = "budget.BudgetDashboard";
}

registry.category("actions").add("budget_dashboard", BudgetDashboard);
