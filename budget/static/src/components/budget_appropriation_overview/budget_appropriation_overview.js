/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";

export class BudgetAppropriationOverview extends Component {

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        
        this.state = useState({
            loading: false,
            error: null,
            filters: {
                fiscal_year_id: null,
                department_ids: [],
                date_from: null,
                date_to: null,
                state: 'all'
            },
            filterOptions: {
                fiscal_years: [],
                departments: [],
                states: []
            },
            hierarchy: [],
            expandedNodes: new Set(),
            totalAmount: 0,
            moveCount: 0,
            lineCount: 0,
            fiscalYears: ""
        });

        // No complex control panel configuration needed

        onWillStart(async () => {
            await this.loadFilterOptions();
            await this.loadData();
        });
    }

    async loadFilterOptions() {
        try {
            const options = await this.orm.call(
                "budget.appropriation.overview.report",
                "get_filter_options",
                []
            );
            this.state.filterOptions = options;
            
            // Set default fiscal year if available
            if (options.fiscal_years.length > 0) {
                this.state.filters.fiscal_year_id = options.fiscal_years[0].id;
            }
        } catch (error) {
            console.error("Error loading filter options:", error);
            this.state.error = "ไม่สามารถโหลดตัวเลือกการกรองได้";
        }
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        
        try {
            const data = await this.orm.call(
                "budget.appropriation.overview.report",
                "get_hierarchical_overview_data",
                [this.state.filters]
            );
            
            this.state.hierarchy = data.hierarchy || [];
            this.state.totalAmount = data.summary.total_amount;
            this.state.moveCount = data.summary.move_count;
            this.state.lineCount = data.summary.line_count;
            this.state.fiscalYears = data.summary.fiscal_years;
        } catch (error) {
            console.error("Error loading data:", error);
            this.state.error = "เกิดข้อผิดพลาดในการโหลดข้อมูล";
        } finally {
            this.state.loading = false;
        }
    }

    // Event handlers
    async onFilterChange() {
        await this.loadData();
    }

    async onFiscalYearChange(fiscalYearId) {
        this.state.filters.fiscal_year_id = fiscalYearId;
        
        // Auto-fill date range based on fiscal year
        const fiscalYear = this.state.filterOptions.fiscal_years.find(fy => fy.id === fiscalYearId);
        if (fiscalYear) {
            this.state.filters.date_from = fiscalYear.date_start;
            this.state.filters.date_to = fiscalYear.date_end;
        }
        
        await this.onFilterChange();
    }

    async onDepartmentChange(departmentId, checked) {
        if (checked) {
            this.state.filters.department_ids.push(departmentId);
        } else {
            const index = this.state.filters.department_ids.indexOf(departmentId);
            if (index > -1) {
                this.state.filters.department_ids.splice(index, 1);
            }
        }
        await this.onFilterChange();
    }

    async onStateChange(stateValue) {
        this.state.filters.state = stateValue;
        await this.onFilterChange();
    }

    async onDateFromChange(date) {
        this.state.filters.date_from = date;
        await this.onFilterChange();
    }

    async onDateToChange(date) {
        this.state.filters.date_to = date;
        await this.onFilterChange();
    }

    onToggleNode(nodeKey) {
        if (this.state.expandedNodes.has(nodeKey)) {
            this.state.expandedNodes.delete(nodeKey);
        } else {
            this.state.expandedNodes.add(nodeKey);
        }
    }

    onExpandAll() {
        this.state.expandedNodes.clear();
        this._expandAllNodes(this.state.hierarchy);
    }

    onCollapseAll() {
        this.state.expandedNodes.clear();
    }

    _expandAllNodes(nodes) {
        for (const node of nodes) {
            if (node.children && node.children.length > 0) {
                this.state.expandedNodes.add(node.key);
                this._expandAllNodes(node.children);
            }
        }
    }

    isNodeExpanded(nodeKey) {
        return this.state.expandedNodes.has(nodeKey);
    }

    async onPrint() {
        await this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: "budget.report_budget_appropriation_overview",
            report_file: "budget.report_budget_appropriation_overview",
            data: {
                filters: this.state.filters,
                hierarchy: this.state.hierarchy,
                summary: {
                    total_amount: this.state.totalAmount,
                    move_count: this.state.moveCount,
                    line_count: this.state.lineCount,
                    fiscal_years: this.state.fiscalYears,
                }
            },
            context: this.env.context,
        });
    }

    async onExport() {
        // Export functionality can be implemented later
        alert("Export functionality will be implemented in the next phase");
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    }

    // Getters
    get selectedFiscalYear() {
        if (!this.state.filters.fiscal_year_id) return null;
        return this.state.filterOptions.fiscal_years.find(
            fy => fy.id === this.state.filters.fiscal_year_id
        );
    }

    get selectedDepartments() {
        return this.state.filterOptions.departments.filter(
            dept => this.state.filters.department_ids.includes(dept.id)
        );
    }

    get selectedState() {
        const state = this.state.filterOptions.states.find(
            s => s.value === this.state.filters.state
        );
        return state ? state.label : 'All';
    }
}

BudgetAppropriationOverview.template = "budget.BudgetAppropriationOverview";
BudgetAppropriationOverview.components = {
    Dropdown,
    DropdownItem,
};

registry.category("actions").add("budget_appropriation_overview", BudgetAppropriationOverview);