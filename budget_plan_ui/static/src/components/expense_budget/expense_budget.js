/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Budget_control_panel } from "../budget_control_panel/budget_control_panel";
import { ExpenseBudgetRenderer } from "./expense_budget_renderer";

export class Expense_budget extends Component {
  setup(){
  }
}

Expense_budget.template = "budget_plan_ui.expense_budget";
Expense_budget.components = {
  Budget_control_panel,
  ExpenseBudgetRenderer,
};
