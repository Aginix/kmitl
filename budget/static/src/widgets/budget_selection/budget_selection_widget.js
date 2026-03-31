/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    getMany2oneId,
    getMany2oneDisplay,
    BUDGET_DIMENSION_FIELDS,
} from "@budget/utils/budget_utils";

export class BudgetSelectionWidget extends Component {
    setup() {
        this.action = useService("action");
    }

    get record() {
        return this.props.record;
    }

    get budgetAccountName() {
        return getMany2oneDisplay(this.record.data, "budget_account_id");
    }

    get activityName() {
        return getMany2oneDisplay(this.record.data, "activity_analytic_id");
    }

    get departmentName() {
        return getMany2oneDisplay(this.record.data, "department_analytic_id");
    }

    get fundName() {
        return getMany2oneDisplay(this.record.data, "fund_analytic_id");
    }

    get sourceName() {
        return getMany2oneDisplay(this.record.data, "source_analytic_id");
    }

    get hasBudgetData() {
        return this.budgetAccountName || this.activityName || this.departmentName || this.fundName || this.sourceName;
    }

    get isEditable() {
        const field = this.record.data["is_budget_editable"];
        if (field !== undefined) return !!field;
        return this.record.mode === "edit";
    }

    async onSelectBudget() {
        const data = this.record.data;
        const context = {
            default_res_model: this.record.resModel,
            default_res_id: this.record.resId,
        };
        for (const fieldName of BUDGET_DIMENSION_FIELDS) {
            context[`default_${fieldName}`] = getMany2oneId(data, fieldName);
        }

        this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: "เลือกงบประมาณ",
                res_model: "budget.selection.wizard",
                views: [[false, "form"]],
                target: "new",
                context: context,
            },
            {
                onClose: async () => {
                    await this.record.load();
                    this.record.model.notify();
                },
            }
        );
    }
}

BudgetSelectionWidget.template = "budget.BudgetSelectionWidget";

registry.category("view_widgets").add("budget_selection", BudgetSelectionWidget);
