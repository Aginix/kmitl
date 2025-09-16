/** @odoo-module **/

import { BudgetAppropriationF4Preview } from "@budget_appropriation/components/budget_appropriation_f4_preview/budget_appropriation_f4_preview";
import { patch } from "@web/core/utils/patch";

// Simple patch for F4 Preview to show offset information
patch(BudgetAppropriationF4Preview.prototype, "budget_appropriation_offset.BudgetAppropriationF4PreviewOffset", {
    
    // ---- Simple Getters ----

    get hasOffsets() {
        return this.appropriation.has_offsets || false;
    },

    get offsetTotal() {
        return this.appropriation.offset_total || 0;
    },

    get totalRevenueNet() {
        return this.appropriation.total_revenue_net || this.totalAmount;
    },

    // ---- Simple Helper Methods ----

    hasNodeOffsets(node) {
        return node.has_offsets && node.offsets && node.offsets.length > 0;
    }
});