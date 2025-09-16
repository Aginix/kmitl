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
                department_ids: [],
                source_analytic_id: null,
                date_from: null,
                date_to: null,
            },
            filterOptions: {
                fiscal_years: [],
                departments: [],
                sources: [],
            },
            showFilters: true,
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

    get selectedDepartments() {
        if (!this.state.filters.department_ids.length) return [];
        return this._findDepartmentsByIds(this.state.filters.department_ids);
    }

    // ---- Event Handlers ----

    onToggleNode(nodeKey) {
        if (this.state.expandedNodes.has(nodeKey)) {
            this.state.expandedNodes.delete(nodeKey);
        } else {
            this.state.expandedNodes.add(nodeKey);
        }
    }

    onExpandAll() {
        const allKeys = this.getAllNodeKeys(this.state.data.hierarchy || []);
        allKeys.forEach(key => this.state.expandedNodes.add(key));
    }

    onCollapseAll() {
        this.state.expandedNodes.clear();
    }

    onToggleFilters() {
        this.state.showFilters = !this.state.showFilters;
    }

    onPrint() {
        // Expand all nodes before printing
        const allKeys = this.getAllNodeKeys(this.state.data.hierarchy || []);
        allKeys.forEach(key => this.state.expandedNodes.add(key));

        // Small delay to ensure DOM is updated before printing
        setTimeout(() => {
            window.print();
        }, 100);
    }

    onRefresh() {
        this.loadData();
    }

    async onApplyFilters() {
        await this.loadData();
    }

    onResetFilters() {
        this.state.filters = {
            fiscal_year_id: this.state.filterOptions.fiscal_years[0]?.id || null,
            department_ids: [],
            source_analytic_id: this.state.filterOptions.sources.find(s => s.code === "1")?.id ||
                               this.state.filterOptions.sources[0]?.id || null,
            date_from: null,
            date_to: null,
        };
        this.loadData();
    }

    // Filter change handlers
    onFiscalYearChange(event) {
        const value = event.target.value;
        this.state.filters.fiscal_year_id = value ? parseInt(value) : null;

        // Auto-set date range based on fiscal year
        if (value) {
            const fy = this.state.filterOptions.fiscal_years.find(f => f.id === parseInt(value));
            if (fy) {
                this.state.filters.date_from = fy.date_from;
                this.state.filters.date_to = fy.date_to;
            }
        }
    }

    onSourceChange(event) {
        const value = event.target.value;
        this.state.filters.source_analytic_id = value ? parseInt(value) : null;
    }

    onDateFromChange(event) {
        this.state.filters.date_from = event.target.value || null;
    }

    onDateToChange(event) {
        this.state.filters.date_to = event.target.value || null;
    }

    onDepartmentChange(departmentId, checked) {
        if (checked) {
            if (!this.state.filters.department_ids.includes(departmentId)) {
                this.state.filters.department_ids.push(departmentId);
            }
        } else {
            this.state.filters.department_ids = this.state.filters.department_ids.filter(
                id => id !== departmentId
            );
        }
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
        if (node.type === 'fund') {
            return 'margin-left: 16px;';
        } else if (node.type === 'account') {
            const marginLeft = 32; // 16px for fund + 16px for account
            return `margin-left: ${marginLeft}px;`;
        }
        return '';
    }

    getNodeIcon(nodeType) {
        const icons = {
            activity: "fa-tasks",
            fund: "fa-coins",
            account: "fa-file-text",
            line: "fa-list-ul"
        };
        return icons[nodeType] || "fa-folder";
    }

    getNodeClass(nodeType, level) {
        const baseClass = "budget-tree-node";
        const typeClass = `node-${nodeType}`;
        const levelClass = `level-${level}`;
        return `${baseClass} ${typeClass} ${levelClass}`;
    }

    getNodeTypeLabel(nodeType) {
        const labels = {
            activity: "กิจกรรม",
            fund: "กองทุน",
            account: "รหัสงบประมาณ",
            line: "รายการ"
        };
        return labels[nodeType] || "";
    }

    _findDepartmentsByIds(ids, departments = null) {
        if (!departments) {
            departments = this.state.filterOptions.departments;
        }

        const result = [];
        for (const dept of departments) {
            if (ids.includes(dept.id)) {
                result.push(dept);
            }
            if (dept.children && dept.children.length > 0) {
                result.push(...this._findDepartmentsByIds(ids, dept.children));
            }
        }
        return result;
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
