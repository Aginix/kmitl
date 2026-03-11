/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BudgetSelectionWidget extends Component {
    setup() {
        this.action = useService("action");
    }

    get record() {
        return this.props.record;
    }

    get budgetAccountName() {
        const val = this.record.data.budget_account_id;
        return val ? (val[1] || val.display_name || "") : "";
    }

    get activityName() {
        const val = this.record.data.activity_analytic_id;
        return val ? (val[1] || val.display_name || "") : "";
    }

    get departmentName() {
        const val = this.record.data.department_analytic_id;
        return val ? (val[1] || val.display_name || "") : "";
    }

    get fundName() {
        const val = this.record.data.fund_analytic_id;
        return val ? (val[1] || val.display_name || "") : "";
    }

    get sourceName() {
        const val = this.record.data.source_analytic_id;
        return val ? (val[1] || val.display_name || "") : "";
    }

    get hasBudgetData() {
        return this.budgetAccountName || this.activityName || this.departmentName || this.fundName || this.sourceName;
    }

    get isEditable() {
        return this.record.mode === "edit";
    }

    _getDefaultValue(fieldName) {
        const val = this.record.data[fieldName];
        if (!val) return false;
        // Many2one fields in record.data are [id, name] or {id, display_name}
        return val[0] || val.id || false;
    }

    async onSelectBudget() {
        const context = {
            default_res_model: this.record.resModel,
            default_res_id: this.record.resId,
            default_budget_account_id: this._getDefaultValue("budget_account_id"),
            default_activity_analytic_id: this._getDefaultValue("activity_analytic_id"),
            default_department_analytic_id: this._getDefaultValue("department_analytic_id"),
            default_fund_analytic_id: this._getDefaultValue("fund_analytic_id"),
            default_source_analytic_id: this._getDefaultValue("source_analytic_id"),
        };

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
