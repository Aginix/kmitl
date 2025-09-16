/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BudgetAppropriationF5Expense extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-left": true,
            "bottom-right": false,
        };

        this.state = useState({
            data: {},
            loading: true,
            error: null,
            expandedNodes: new Set(),
            filters: {
                fiscal_year_id: null,
                department_id: null,
                source_analytic_id: null,
            },
            filterOptions: {
                fiscal_years: [],
                departments: [],
                sources: [],
            },
        });

        this.orm = useService("orm");
        this.notification = useService("notification");

        onWillStart(async () => {
            await this.loadFilterOptions();
            await this.loadData();
        });
    }

    async loadFilterOptions() {
        try {
            const options = await this.orm.call(
                "budget.appropriation.f5.expense",
                "get_filter_options",
                []
            );
            this.state.filterOptions = options;

            // Set default fiscal year if available
            if (options.fiscal_years.length > 0) {
                this.state.filters.fiscal_year_id = options.fiscal_years[0].id;
            }

            // Set default source if available
            if (options.sources.length > 0) {
                const defaultSource = options.sources.find(s => s.code === "1") || options.sources[0];
                this.state.filters.source_analytic_id = defaultSource.id;
            }
        } catch (error) {
            console.error("Error loading filter options:", error);
            this.notification.add("เกิดข้อผิดพลาดในการโหลดตัวเลือกตัวกรอง", { type: "danger" });
        }
    }

    async loadData() {
        try {
            this.state.loading = true;
            this.state.error = null;

            const result = await this.orm.call(
                "budget.appropriation.f5.expense",
                "get_data",
                [this.state.filters]
            );

            this.state.data = result;

            // Auto-expand all nodes by default
            if (result.hierarchy && result.hierarchy.length > 0) {
                const allKeys = this.getAllNodeKeys(result.hierarchy);
                allKeys.forEach(key => this.state.expandedNodes.add(key));
            }

        } catch (error) {
            console.error("Error loading budget appropriation data:", error);
            this.state.error = error.message || "เกิดข้อผิดพลาดในการโหลดข้อมูล";
            this.notification.add("เกิดข้อผิดพลาดในการโหลดข้อมูล", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    // ---- Getters ----

    get hierarchy() {
        return this.state.data.hierarchy || [];
    }

    get summary() {
        return this.state.data.summary || {};
    }

    get filters() {
        return this.state.data.filters || {};
    }

    get currentDate() {
        return this.state.data.current_date || "";
    }

    get selectedFiscalYear() {
        if (!this.state.filters.fiscal_year_id) return null;
        return this.state.filterOptions.fiscal_years.find(
            fy => fy.id === this.state.filters.fiscal_year_id
        );
    }

    get selectedSource() {
        if (!this.state.filters.source_analytic_id) return null;
        return this.state.filterOptions.sources.find(
            source => source.id === this.state.filters.source_analytic_id
        );
    }

    get selectedDepartment() {
        if (!this.state.filters.department_id) return null;
        return this.flatDepartmentOptions.find(
            dept => dept.id === this.state.filters.department_id
        );
    }

    get totalBalance() {
        return this.summary.total_amount || 0;
    }

    // ---- Event Handlers ----

    onToggleNode(nodeKey) {
        if (this.state.expandedNodes.has(nodeKey)) {
            this.state.expandedNodes.delete(nodeKey);
        } else {
            this.state.expandedNodes.add(nodeKey);
        }
    }


    onPrint() {}

    onRefresh() {
        this.loadData();
    }

    async onFilterChange() {
        await this.loadData();
    }

    async onFiscalYearChange(e) {
        const fiscalYearId = e.target.value ? Number(e.target.value) : null;
        this.state.filters.fiscal_year_id = fiscalYearId;
        await this.onFilterChange();
    }

    async onSourceChange(e) {
        this.state.filters.source_analytic_id = e.target.value ? Number(e.target.value) : null;
        await this.onFilterChange();
    }

    async onDepartmentChange(e) {
        this.state.filters.department_id = e.target.value ? Number(e.target.value) : null;
        await this.onFilterChange();
    }

    // ---- Helper Methods ----

    getAllNodeKeys(nodes) {
        const keys = [];
        for (const node of nodes) {
            keys.push(node.key);
            if (node.children && node.children.length > 0) {
                keys.push(...this.getAllNodeKeys(node.children));
            }
        }
        return keys;
    }

    isNodeExpanded(nodeKey) {
        return this.state.expandedNodes.has(nodeKey);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    }

    getMarginStyle(node) {
        const marginLeft = node.level * 20;
        return `margin-left: ${marginLeft}px;`;
    }

    getNodeClass(nodeType, level) {
        return "budget-tree-node";
    }

    _renderDepartmentOption(dept, level = 0) {
        const indent = "—".repeat(level);
        return {
            id: dept.id,
            name: `${indent} ${dept.complete_name || dept.name}`,
            code: dept.code,
            level: level,
            children: dept.children || []
        };
    }

    get flatDepartmentOptions() {
        const flatten = (departments, level = 0) => {
            const result = [];
            for (const dept of departments) {
                result.push(this._renderDepartmentOption(dept, level));
                if (dept.children && dept.children.length > 0) {
                    result.push(...flatten(dept.children, level + 1));
                }
            }
            return result;
        };
        return flatten(this.state.filterOptions.departments);
    }
}

BudgetAppropriationF5Expense.template = "budget_appropriation_report.BudgetAppropriationF5Expense";
BudgetAppropriationF5Expense.components = {
    ControlPanel
};

registry.category("actions").add("budget_appropriation_f5_expense_overview_report", BudgetAppropriationF5Expense);
