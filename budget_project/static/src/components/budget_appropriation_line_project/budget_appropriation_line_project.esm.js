/** @odoo-module **/

import {BudgetAppropriationLineRenderer} from "@budget_appropriation/components/budget_appropriation_line/budget_appropriation_line.esm";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(
    BudgetAppropriationLineRenderer.prototype,
    "project_budget.BudgetAppropriationLineBudgetRenderer",
    {
        setup() {
            this._super(...arguments);
            this.orm = useService("orm");
        },
        getProjectRows(record) {
            return this.env.model.root.data.project_ids.records.filter(
                (project) =>
                    project.data.budget_appropriation_line_id[0] === record.data.id
            );
        },
        formatCurrency(amount) {
            return new Intl.NumberFormat("th-TH", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
            }).format(amount);
        },
        getTotalBalance(record) {
            const project_ids = this.env.model.root.data.project_ids.records.filter(
                (project) =>
                    project.data.budget_appropriation_line_id[0] === record.data.id
            );
            const sum = project_ids.map(record => record.data.amount).reduce((p, c) => p + c, 0)
            return sum
        },
        getRemainingBalance(record) {
            return record.data.balance - this.getTotalBalance(record)
        }
    }
);
