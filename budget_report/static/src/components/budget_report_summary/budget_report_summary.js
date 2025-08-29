/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {DepartmentFilter} from "../department_filter/department_filter";

export class BudgetReportSummary extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-left": true,
            "bottom-right": false
        };

        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            filters: {
                fiscal_year_id: null,
                source_analytic_id: null,
                department_ids: [],
            },
            loading: false,
            rows: [],
            fiscalYear: null,
            sourceAnalytic: null,
            departments: null,
            selectedDepartmentIds: [],
            showSidebar: true,
            expandedRows: new Set(), // Track expanded rows
            filterOptions: {
                fiscal_years: [],
                departments: [],
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const response = await this.orm.call(
                "budget.report.summary",
                "get_data",
                [this.state.filters]
            );

            this.state.rows = response.rows;
            this.state.fiscalYear = response.fiscal_year;
            this.state.sourceAnalytic = response.source_analytic;
            this.state.filters = response.filters;
            this.state.departments = response.departments || null;

            this.state.filterOptions = await this.orm.call(
                "budget.report.summary",
                "get_filter_options",
                []
            );
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add("เกิดข้อผิดพลาดในการโหลดข้อมูล: " + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    onRefresh() {
        this.loadData()
    }

    onPrint() {}

    get departments() {
        return this.state.departments;
    }

    get rows() {
        return this.state.rows
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    }

    async onFilterChange() {
        await this.loadData()
    }

    async onFiscalYearChange(e) {
        this.onChangeBy('fiscal_year_id', e.target.value ? Number(e.target.value) : null)
    }

    async onChangeBy(name, value) {
        this.state.filters[name] = value
        await this.onFilterChange();
    }

    async onSourceAnalyticIdChange(e) {
        this.onChangeBy('source_analytic_id', e.target.value ? Number(e.target.value) : null)
    }

    onDepartmentSelectionChange(selectedIds) {
        this.state.selectedDepartmentIds = selectedIds;
        this.state.filters.department_ids = selectedIds;
        this.loadData();
    }

    get departmentHierarchy() {
        return this.state.filterOptions.departments || [];
    }

    // Expand/Collapse functionality
    toggleRow(event) {
        const rowKey = event.currentTarget.getAttribute('data-row-key');
        if (!rowKey) return;
        
        // Create a new Set to ensure OWL detects the state change properly
        const newExpandedRows = new Set(this.state.expandedRows);
        if (newExpandedRows.has(rowKey)) {
            newExpandedRows.delete(rowKey);
        } else {
            newExpandedRows.add(rowKey);
        }
        this.state.expandedRows = newExpandedRows;
    }

    isRowExpanded(rowKey) {
        return this.state.expandedRows.has(rowKey);
    }

    isRowVisible(row) {
        if (!row || !this.state.rows || !row.row_key) {
            return false;
        }
        
        if (!row.parent_row_id) {
            return true; // Root rows are always visible
        }
        
        // Find parent row
        const parentRow = this.state.rows.find(r => r && r.row_key === row.parent_row_id);
        if (!parentRow || !parentRow.row_key) {
            return true; // Show row if parent not found (defensive)
        }
        
        // Row is visible if parent is expanded and parent is visible (recursive)
        return this.isRowExpanded(parentRow.row_key) && this.isRowVisible(parentRow);
    }

    get visibleRows() {
        if (!this.state.rows || !Array.isArray(this.state.rows)) {
            return [];
        }
        return this.state.rows.filter(row => row && row.row_key && this.isRowVisible(row));
    }

    expandAll() {
        if (!this.state.rows || !Array.isArray(this.state.rows)) {
            return;
        }
        
        // Create a new Set with all rows that have children
        const newExpandedRows = new Set();
        this.state.rows.forEach(row => {
            if (row && row.has_children && row.row_key) {
                newExpandedRows.add(row.row_key);
            }
        });
        this.state.expandedRows = newExpandedRows;
    }

    collapseAll() {
        // Create a new empty Set to ensure OWL detects the change
        this.state.expandedRows = new Set();
    }

    // Get expand toggle icon class
    getExpandIcon(row) {
        if (!row || !row.has_children || !row.row_key) return '';
        return this.isRowExpanded(row.row_key) ? 'fa fa-caret-down' : 'fa fa-caret-right';
    }
}

BudgetReportSummary.template = "budget_report.BudgetReportSummary";
BudgetReportSummary.components = {
    ControlPanel,
    DepartmentFilter
};

registry
    .category("actions")
    .add("budget_report_summary", BudgetReportSummary);
