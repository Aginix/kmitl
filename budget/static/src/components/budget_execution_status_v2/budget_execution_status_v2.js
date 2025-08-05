/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class BudgetExecutionStatusV2 extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        // Simple state management
        this.state = useState({
            isLoading: true,
            data: [],
            summary: {},
            filters: {
                date_range_fy_id: null,
                date_from: null,
                date_to: null
            },
            fiscalYears: [],
            expandedNodes: new Set()
        });
        
        onWillStart(async () => {
            await this.loadInitialData();
        });
    }
    
    async loadInitialData() {
        try {
            // Get filter options
            const options = await this.orm.call(
                "budget.execution.status.report",
                "get_filter_options",
                []
            );
            
            this.state.fiscalYears = options.fiscal_years || [];
            
            // Set default fiscal year
            const currentFY = this.state.fiscalYears.find(fy => fy.is_current);
            if (currentFY) {
                this.state.filters.date_range_fy_id = currentFY.id;
                this.state.filters.date_from = currentFY.date_start;
                this.state.filters.date_to = currentFY.date_end;
            }
            
            // Load report data
            await this.loadReportData();
            
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add("Failed to load report data", { type: "danger" });
        } finally {
            this.state.isLoading = false;
        }
    }
    
    async loadReportData() {
        const result = await this.orm.call(
            "budget.execution.status.report",
            "get_report_data",
            [this.state.filters]
        );
        
        this.state.data = result.hierarchical_data || [];
        this.state.summary = result.summary || {};
    }
    
    // Event handlers
    async onFiscalYearChange(event) {
        const fyId = parseInt(event.target.value);
        const fy = this.state.fiscalYears.find(f => f.id === fyId);
        
        if (fy) {
            this.state.filters.date_range_fy_id = fyId;
            this.state.filters.date_from = fy.date_start;
            this.state.filters.date_to = fy.date_end;
            
            this.state.isLoading = true;
            await this.loadReportData();
            this.state.isLoading = false;
        }
    }
    
    toggleNode(nodeId) {
        if (this.state.expandedNodes.has(nodeId)) {
            this.state.expandedNodes.delete(nodeId);
        } else {
            this.state.expandedNodes.add(nodeId);
        }
    }
    
    isNodeExpanded(nodeId) {
        return this.state.expandedNodes.has(nodeId);
    }
    
    // Formatting helpers
    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            style: 'currency',
            currency: 'THB',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount || 0);
    }
    
    formatPercentage(value) {
        return `${(value || 0).toFixed(2)}%`;
    }
    
    getUtilizationClass(utilization) {
        if (utilization > 90) return 'text-danger';
        if (utilization > 70) return 'text-warning';
        return 'text-success';
    }
}

BudgetExecutionStatusV2.template = "budget.BudgetExecutionStatusV2";

registry.category("actions").add("budget_execution_status_v2", BudgetExecutionStatusV2);