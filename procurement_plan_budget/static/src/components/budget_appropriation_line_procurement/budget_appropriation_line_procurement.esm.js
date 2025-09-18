/** @odoo-module **/

import {BudgetAppropriationLineRenderer} from "@budget_appropriation/components/budget_appropriation_line/budget_appropriation_line.esm";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(
    BudgetAppropriationLineRenderer.prototype,
    "procurement_plan_budget.BudgetAppropriationLineProcurementRenderer",
    {
        setup() {
            this._super(...arguments);
            this.orm = useService("orm");
        },
        getProcurementRows(record) {
            return this.env.model.root.data.procurement_plan_ids.records.filter(
                (procurement) =>
                    procurement.data.budget_appropriation_line_id[0] === record.data.id
            );
        },
        formatCurrency(amount) {
            return new Intl.NumberFormat("th-TH", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
            }).format(amount);
        },
        getAllocationAmount(record) {
            const procurement_plan_ids = this.env.model.root.data.procurement_plan_ids.records.filter(
                (procurement) =>
                    procurement.data.budget_appropriation_line_id[0] === record.data.id
            );
            const sum = procurement_plan_ids.map(record => record.data.total_price).reduce((p, c) => p + c, 0)

            const _super = this._super.bind(this);
            return sum + _super(...arguments)
        },
        getAvailableAmount(record) {
            return record.data.balance - this.getAllocationAmount(record)
        }
    }
);
