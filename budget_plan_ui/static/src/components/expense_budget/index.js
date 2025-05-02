/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Expense_budget } from "./expense_budget";

registry.category("actions").add("expense_budget", Expense_budget);
