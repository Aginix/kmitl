/** @odoo-module **/

import {BudgetAppropriationLineRenderer} from "@budget_appropriation/components/budget_appropriation_line/budget_appropriation_line.esm";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(
    BudgetAppropriationLineRenderer.prototype,
    "budget_appropriation_offset.BudgetAppropriationLineOffsetRenderer",
    {
        setup() {
            this._super(...arguments);
            this.orm = useService("orm");
        },
        getOffsetRows(record) {
            return this.env.model.root.data.offset_ids.records.filter(
                (item) =>
                    item.data.appropriation_line_id[0] === record.data.id
            );
        },
        formatCurrency(amount) {
            return new Intl.NumberFormat("th-TH", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
            }).format(amount);
        },
        getTotalOffset(record) {
            const offset_ids = this.env.model.root.data.offset_ids.records.filter(
                (item) =>
                    item.data.appropriation_line_id[0] === record.data.id
            );
            const sum = offset_ids.map(record => record.data.amount).reduce((p, c) => p + c, 0)
            return sum
        },
        getRevenueBalance(record) {
                return record.data.balance - this.getTotalOffset(record)
        }
    }
);
