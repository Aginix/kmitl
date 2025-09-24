/** @odoo-module **/

import { BudgetAppropriationF4Preview } from "@budget_appropriation/components/budget_appropriation_f4_preview/budget_appropriation_f4_preview";
import { patch } from "@web/core/utils/patch";

// Simple patch for F4 Preview to show offset information
patch(BudgetAppropriationF4Preview.prototype, "budget_appropriation_offset.BudgetAppropriationF4PreviewOffset", {
    
    // ---- Simple Helper Methods ----

    hasOffsetsData() {
        return this.appropriation.has_offsets || false;
    },

    getOffsetTotal() {
        return this.appropriation.offset_total || 0;
    },

    getTotalRevenueNet() {
        return this.appropriation.total_revenue_net || this.totalAmount;
    },

    hasNodeOffsets(node) {
        return node.has_offsets && node.offsets && node.offsets.length > 0;
    }
});