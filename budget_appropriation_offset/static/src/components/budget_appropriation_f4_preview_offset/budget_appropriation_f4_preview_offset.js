/** @odoo-module **/

import { BudgetAppropriationF4Preview } from "@budget_appropriation/components/budget_appropriation_f4_preview/budget_appropriation_f4_preview";
import { patch } from "@web/core/utils/patch";

// Patch the F4 Preview component to enhance with offset functionality
patch(BudgetAppropriationF4Preview.prototype, "budget_appropriation_offset.BudgetAppropriationF4PreviewOffset", {
    
    setup() {
        this._super(...arguments);
        
        // Add offset-specific state
        Object.assign(this.state, {
            showOffsets: true,
            showNetAmounts: true,
        });
    },

    // ---- Enhanced Getters ----

    get hasOffsets() {
        return this.appropriation.has_offsets || false;
    },

    get offsetTotal() {
        return this.appropriation.offset_total || 0;
    },

    get totalRevenueNet() {
        return this.appropriation.total_revenue_net || this.totalAmount;
    },

    // ---- Enhanced Event Handlers ----

    onToggleOffsets() {
        this.state.showOffsets = !this.state.showOffsets;
    },

    onToggleNetAmounts() {
        this.state.showNetAmounts = !this.state.showNetAmounts;
    },

    // ---- Enhanced Helper Methods ----

    formatCurrencyWithSign(amount) {
        const formatted = this.formatCurrency(Math.abs(amount));
        return amount >= 0 ? formatted : `(${formatted})`;
    },

    getOffsetStateClass(state) {
        const stateClasses = {
            'draft': 'badge-secondary',
            'waiting_to_process': 'badge-warning',
            'done': 'badge-success',
            'cancelled': 'badge-danger'
        };
        return stateClasses[state] || 'badge-secondary';
    },

    hasNodeOffsets(node) {
        return node.has_offsets && node.offsets && node.offsets.length > 0;
    },

    getNodeNetAmount(node) {
        if (this.state.showNetAmounts && node.has_offsets) {
            return node.net_amount || 0;
        }
        return node.total_amount || 0;
    },

    getNodeDisplayAmount(node) {
        if (this.state.showNetAmounts && node.has_offsets) {
            return {
                gross: node.total_amount || 0,
                offset: node.offset_total || 0,
                net: node.net_amount || 0,
                showBreakdown: true
            };
        }
        return {
            gross: node.total_amount || 0,
            offset: 0,
            net: node.total_amount || 0,
            showBreakdown: false
        };
    },

    getOffsetIcon(offset) {
        const stateIcons = {
            'draft': 'fa-pencil',
            'waiting_to_process': 'fa-clock-o',
            'done': 'fa-check',
            'cancelled': 'fa-times'
        };
        return stateIcons[offset.state] || 'fa-exchange';
    }
});

// Extend the template name to use the enhanced version
patch(BudgetAppropriationF4Preview, "budget_appropriation_offset.BudgetAppropriationF4PreviewOffsetTemplate", {
    template: "budget_appropriation_offset.BudgetAppropriationF4PreviewOffset",
});