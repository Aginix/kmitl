/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Budget_control_panel } from "../budget_control_panel/budget_control_panel";
import { RevenueBudgetRenderer } from "./revenue_budget_renderer";

export class Revenue_budget extends Component {
  setup() {}
}
Revenue_budget.template = "budget_plan_ui.revenue_budget";
Revenue_budget.components = { Budget_control_panel, RevenueBudgetRenderer };
