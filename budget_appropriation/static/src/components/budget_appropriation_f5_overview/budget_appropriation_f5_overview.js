/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class BudgetAppropriationF5Overview extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            data: null,
            loading: true,
            error: null,
            expandedNodes: new Set(),
            showFilters: false,
            filters: {
                fiscal_year_id: false,
                department_ids: [],
                activity_ids: [],
                fund_ids: [],
                source_ids: [],
                state: false,
                include_zero_amounts: false
            }
        });

        onWillStart(async () => {
            await this.loadDefaultFilters();
            await this.loadOverviewData();
        });
    }

    async loadDefaultFilters() {
        try {
            const defaults = await this.orm.call(
                "budget.appropriation.f5.overview",
                "get_default_filters",
                []
            );
            Object.assign(this.state.filters, defaults);
        } catch (error) {
            console.error("Error loading default filters:", error);
        }
    }

    async loadOverviewData() {
        this.state.loading = true;
        this.state.error = null;
        
        try {
            const options = { ...this.state.filters };
            
            const data = await this.orm.call(
                "budget.appropriation.f5.overview",
                "get_f5_overview_data",
                [],
                { options }
            );
            
            this.state.data = data;
            
            // Auto-expand first level nodes
            if (data.hierarchy) {
                data.hierarchy.forEach(node => {
                    this.state.expandedNodes.add(node.key);
                });
            }
            
        } catch (error) {
            console.error("Error loading overview data:", error);
            this.state.error = error.message || "Failed to load overview data";
            this.notification.add("Failed to load overview data", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    // Node Management
    onToggleNode(nodeKey) {
        if (this.state.expandedNodes.has(nodeKey)) {
            this.state.expandedNodes.delete(nodeKey);
        } else {
            this.state.expandedNodes.add(nodeKey);
        }
    }

    isNodeExpanded(nodeKey) {
        return this.state.expandedNodes.has(nodeKey);
    }

    onExpandAll() {
        const addAllKeys = (nodes) => {
            nodes.forEach(node => {
                this.state.expandedNodes.add(node.key);
                if (node.children) {
                    addAllKeys(node.children);
                }
            });
        };
        
        if (this.state.data?.hierarchy) {
            addAllKeys(this.state.data.hierarchy);
        }
    }

    onCollapseAll() {
        this.state.expandedNodes.clear();
    }

    // Filter Management
    onToggleFilters() {
        this.state.showFilters = !this.state.showFilters;
    }

    async onApplyFilters() {
        await this.loadOverviewData();
        this.state.showFilters = false;
        this.notification.add("Filters applied successfully", { type: "success" });
    }

    onResetFilters() {
        this.state.filters = {
            fiscal_year_id: false,
            department_ids: [],
            activity_ids: [],
            fund_ids: [],
            source_ids: [],
            state: false,
            include_zero_amounts: false
        };
    }

    // Actions
    async onRefresh() {
        await this.loadOverviewData();
        this.notification.add("Data refreshed", { type: "success" });
    }

    onPrint() {
        window.print();
    }

    onExport() {
        // TODO: Implement export functionality
        this.notification.add("Export functionality coming soon", { type: "info" });
    }

    onBack() {
        this.action.doAction({
            type: 'ir.actions.act_window_close'
        });
    }

    // Helpers
    formatCurrency(amount) {
        if (amount === 0) return "-";
        return new Intl.NumberFormat('th-TH', {
            style: 'currency',
            currency: 'THB',
            minimumFractionDigits: 2
        }).format(amount);
    }

    getMarginStyle(node) {
        if (node.type === 'fund') {
            return 'margin-left: 16px;';
        } else if (node.type === 'account') {
            // For account: 16px + (16px * account_level) where account_level starts from 1
            // Tree levels: Root=0, Activity=1, Fund=2, Account=3+
            // Account level relative to fund = node.level - 2 (subtract root, activity, fund)
            // But we want first account to be level 1, so: Math.max(1, node.level - 2)
            const accountLevel = Math.max(1, node.level - 2); // Account level starts from 1
            const marginLeft = 16 + (16 * accountLevel);
            return `margin-left: ${marginLeft}px;`;
        }
        return '';
    }

    getAllNodeKeys() {
        const keys = new Set();
        const collectKeys = (nodes) => {
            nodes.forEach(node => {
                keys.add(node.key);
                if (node.children) {
                    collectKeys(node.children);
                }
            });
        };
        
        if (this.state.data?.hierarchy) {
            collectKeys(this.state.data.hierarchy);
        }
        
        return keys;
    }

    getStateDisplayName(state) {
        const stateNames = {
            'draft': 'Draft',
            'review': 'Under Review',
            'posted': 'Posted',
            'cancel': 'Cancelled'
        };
        return stateNames[state] || state;
    }
}

BudgetAppropriationF5Overview.template = "budget_appropriation.F5Overview";

registry.category("actions").add("budget_appropriation_f5_overview", BudgetAppropriationF5Overview);