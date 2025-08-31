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
        this.actionService = useService("action");

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

    // Drill-down functionality
    // Helper to check if a cell value is clickable (not zero)
    isClickable(value) {
        return value && value !== 0;
    }

    // Handler for งบประมาณ (Appropriation) column
    async onAppropriationClick(event) {
        event.stopPropagation();
        event.preventDefault();
        
        const row = JSON.parse(event.currentTarget.getAttribute('data-row'));
        const domain = this._buildMoveLineDomain(row, ['appropriation', 'entry']);
        
        await this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `งบประมาณ - ${row.code} ${row.name}`,
            res_model: 'budget.move.line',
            views: [[false, 'tree'], [false, 'form'], [false, 'pivot']],
            domain: domain,
            context: {
                search_default_group_by_account: 1,
                search_default_group_by_move: 1,
            },
            target: 'current',
        });
    }

    // Handler for เงินจอง (Commitment) column  
    async onCommitmentClick(event) {
        event.stopPropagation();
        event.preventDefault();
        
        const row = JSON.parse(event.currentTarget.getAttribute('data-row'));
        const domain = this._buildCommitmentDomain(row, 'reserved');
        
        await this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `เงินจอง - ${row.code} ${row.name}`,
            res_model: 'budget.commitment',
            views: [[false, 'tree'], [false, 'form'], [false, 'pivot']],
            domain: domain,
            context: {
                search_default_state_reserved: 1,
            },
            target: 'current',
        });
    }

    // Handler for ผูกพัน (Obligation) column
    async onObligationClick(event) {
        event.stopPropagation();
        event.preventDefault();
        
        const row = JSON.parse(event.currentTarget.getAttribute('data-row'));
        const domain = this._buildCommitmentDomain(row, 'obligated');
        
        await this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `ผูกพัน - ${row.code} ${row.name}`,
            res_model: 'budget.commitment',
            views: [[false, 'tree'], [false, 'form'], [false, 'pivot']],
            domain: domain,
            context: {
                search_default_state_obligated: 1,
            },
            target: 'current',
        });
    }

    // Handler for เบิกจ่ายแล้ว (Expenditure) column
    async onExpenditureClick(event) {
        event.stopPropagation();
        event.preventDefault();
        
        const row = JSON.parse(event.currentTarget.getAttribute('data-row'));
        const domain = this._buildMoveLineDomain(row, ['consume']);
        
        await this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `เบิกจ่ายแล้ว - ${row.code} ${row.name}`,
            res_model: 'budget.move.line',
            views: [[false, 'tree'], [false, 'form'], [false, 'pivot']],
            domain: domain,
            context: {
                search_default_group_by_move: 1,
            },
            target: 'current',
        });
    }

    // Build domain for budget.move.line queries
    _buildMoveLineDomain(row, moveTypes) {
        const domain = [
            ['parent_state', '=', 'posted'],
            ['date_range_fy_id', '=', this.state.filters.fiscal_year_id],
        ];
        
        // Add source analytic filter
        if (this.state.filters.source_analytic_id) {
            domain.push(['source_analytic_id', '=', this.state.filters.source_analytic_id]);
        }
        
        // Add department filter from report filters
        if (this.state.filters.department_ids && this.state.filters.department_ids.length > 0) {
            const deptIds = this._getDepartmentWithChildren(this.state.filters.department_ids);
            domain.push(['department_analytic_id', 'in', deptIds]);
        }
        
        // Add move type filter
        if (moveTypes && moveTypes.length > 0) {
            domain.push(['move_type', 'in', moveTypes]);
        }
        
        // Add row-specific analytic filters based on row type
        this._addRowAnalyticFilters(domain, row);
        
        return domain;
    }

    // Build domain for budget.commitment queries
    _buildCommitmentDomain(row, state) {
        const domain = [
            ['state', '=', state],
            ['date_range_fy_id', '=', this.state.filters.fiscal_year_id],
        ];
        
        // Add source analytic filter
        if (this.state.filters.source_analytic_id) {
            domain.push(['source_analytic_id', '=', this.state.filters.source_analytic_id]);
        }
        
        // Add department filter from report filters
        if (this.state.filters.department_ids && this.state.filters.department_ids.length > 0) {
            const deptIds = this._getDepartmentWithChildren(this.state.filters.department_ids);
            domain.push(['department_analytic_id', 'in', deptIds]);
        }
        
        // Add row-specific analytic filters
        this._addRowAnalyticFilters(domain, row);
        
        return domain;
    }

    // Add analytic filters based on row context
    _addRowAnalyticFilters(domain, row) {
        // Determine which dimension we're filtering on based on row type
        if (row.type === 'activity') {
            // For activity rows, filter by activity and its children
            const activityIds = this._getAnalyticWithChildren(row.id, row.parent_path);
            domain.push(['activity_analytic_id', 'in', activityIds]);
        } else if (row.type === 'fund') {
            // For fund rows, need to filter by parent activity AND fund
            if (row.parent_activity_id) {
                const activityIds = this._getAnalyticWithChildren(
                    row.parent_activity_id, 
                    row.parent_activity_path
                );
                domain.push(['activity_analytic_id', 'in', activityIds]);
            }
            const fundIds = this._getAnalyticWithChildren(row.id, row.parent_path);
            domain.push(['fund_analytic_id', 'in', fundIds]);
        } else if (row.type === 'account') {
            // For account rows, filter by all parent dimensions
            if (row.parent_activity_id) {
                const activityIds = this._getAnalyticWithChildren(
                    row.parent_activity_id,
                    row.parent_activity_path
                );
                domain.push(['activity_analytic_id', 'in', activityIds]);
            }
            if (row.parent_fund_id) {
                const fundIds = this._getAnalyticWithChildren(
                    row.parent_fund_id,
                    row.parent_fund_path
                );
                domain.push(['fund_analytic_id', 'in', fundIds]);
            }
            // Filter by specific budget account
            domain.push(['account_id', '=', row.id]);
        }
    }

    // Get analytic IDs including children (for hierarchical filtering)
    _getAnalyticWithChildren(analyticId, parentPath) {
        // For now, return just the ID
        // Future enhancement: call server method for hierarchical expansion
        // const children = await this.orm.call(
        //     "budget.report.summary", 
        //     "get_analytic_children", 
        //     [analyticId, dimension]
        // );
        return [analyticId];
    }

    // Get department IDs including children
    _getDepartmentWithChildren(departmentIds) {
        // For now, return the original list
        // This could be enhanced to expand to include child departments
        return departmentIds;
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
