/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Revenue_budget } from "./revenue_budget";

registry.category("actions").add("revenue_budget", Revenue_budget);