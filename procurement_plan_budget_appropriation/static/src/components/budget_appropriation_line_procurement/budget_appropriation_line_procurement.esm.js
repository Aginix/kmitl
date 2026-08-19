/** @odoo-module **/

import {BudgetAppropriationLineRenderer} from "@budget_appropriation/components/budget_appropriation_line/budget_appropriation_line.esm";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(
    BudgetAppropriationLineRenderer.prototype,
    "procurement_plan_budget_appropriation.BudgetAppropriationLineProcurementRenderer",
    {
        setup() {
            this._super(...arguments);
            this.orm = useService("orm");
        },
    }
);
