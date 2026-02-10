/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import {DepartmentFilter} from "../department_filter/department_filter";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

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

        this._filterOptionsLoaded = false;

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

            if (!this._filterOptionsLoaded) {
                this.state.filterOptions = await this.orm.call(
                    "budget.report.summary",
                    "get_filter_options",
                    []
                );
                this._filterOptionsLoaded = true;
            }
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

    get visibleRows() {
        if (!this.state.rows || !Array.isArray(this.state.rows)) {
            return [];
        }

        // Build O(1) lookup map
        const rowMap = new Map();
        for (const row of this.state.rows) {
            if (row && row.row_key) {
                rowMap.set(row.row_key, row);
            }
        }

        // Cache visibility results
        const cache = new Map();
        const isVisible = (row) => {
            if (!row || !row.row_key) return false;
            if (cache.has(row.row_key)) return cache.get(row.row_key);

            let result;
            if (!row.parent_row_id) {
                result = true;
            } else {
                const parentRow = rowMap.get(row.parent_row_id);
                if (!parentRow || !parentRow.row_key) {
                    result = true;
                } else {
                    result = this.isRowExpanded(parentRow.row_key) && isVisible(parentRow);
                }
            }
            cache.set(row.row_key, result);
            return result;
        };

        return this.state.rows.filter(row => row && row.row_key && isVisible(row));
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

    // Helper to find row by row_key
    _findRowByKey(rowKey) {
        return this.state.rows.find(row => row.row_key === rowKey);
    }

    // Handler for งบประมาณ (Appropriation) column
    async onAppropriationClick(event) {
        event.stopPropagation();
        event.preventDefault();

        const rowKey = event.currentTarget.getAttribute('data-row-key');
        const row = this._findRowByKey(rowKey);
        if (!row) return;

        const domain = await this._buildMoveLineDomain(row, ['appropriation', 'entry']);

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

        const rowKey = event.currentTarget.getAttribute('data-row-key');
        const row = this._findRowByKey(rowKey);
        if (!row) return;

        const domain = await this._buildCommitmentDomain(row, 'reserved');

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

        const rowKey = event.currentTarget.getAttribute('data-row-key');
        const row = this._findRowByKey(rowKey);
        if (!row) return;

        const domain = await this._buildCommitmentDomain(row, 'obligated');

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

        const rowKey = event.currentTarget.getAttribute('data-row-key');
        const row = this._findRowByKey(rowKey);
        if (!row) return;

        const domain = await this._buildMoveLineDomain(row, ['consume']);

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
    async _buildMoveLineDomain(row, moveTypes) {
        const domain = [
            ['parent_state', '=', 'posted'],
            ['account_fiscal_year_id', '=', this.state.filters.fiscal_year_id],
        ];

        // Add source analytic filter
        if (this.state.filters.source_analytic_id) {
            domain.push(['source_analytic_id', '=', this.state.filters.source_analytic_id]);
        }

        // Add department filter from report filters
        if (this.state.filters.department_ids && this.state.filters.department_ids.length > 0) {
            const deptIds = await this._getDepartmentWithChildren(this.state.filters.department_ids);
            domain.push(['department_analytic_id', 'in', deptIds]);
        }

        // Add move type filter
        if (moveTypes && moveTypes.length > 0) {
            domain.push(['move_type', 'in', moveTypes]);
        }

        // Add row-specific analytic filters based on row type
        await this._addRowAnalyticFilters(domain, row);

        return domain;
    }

    // Build domain for budget.commitment queries
    async _buildCommitmentDomain(row, state) {
        const domain = [
            ['state', '=', state],
            ['account_fiscal_year_id', '=', this.state.filters.fiscal_year_id],
        ];

        // Add source analytic filter
        if (this.state.filters.source_analytic_id) {
            domain.push(['source_analytic_id', '=', this.state.filters.source_analytic_id]);
        }

        // Add department filter from report filters
        if (this.state.filters.department_ids && this.state.filters.department_ids.length > 0) {
            const deptIds = await this._getDepartmentWithChildren(this.state.filters.department_ids);
            domain.push(['department_analytic_id', 'in', deptIds]);
        }

        // Add row-specific analytic filters
        await this._addRowAnalyticFilters(domain, row);

        return domain;
    }

    // Add analytic filters based on row context using code-based filtering
    async _addRowAnalyticFilters(domain, row) {
        // Use code-based filtering with ilike for simpler and more reliable filtering
        if (row.type === 'activity') {
            // For activity rows, filter by activity code and its children using prefix
            if (row.code) {
                // Use analytic account code prefix matching
                await this._addAnalyticCodeFilter(domain, 'activity_analytic_id', row.code);

                // Also get budget accounts that start with this activity code
                await this._addBudgetAccountCodeFilter(domain, row.code);
            }
        } else if (row.type === 'fund') {
            // For fund rows, filter by fund code and parent activity if exists
            if (row.parent_activity_code) {
                await this._addAnalyticCodeFilter(domain, 'activity_analytic_id', row.parent_activity_code);
            }
            if (row.code) {
                await this._addAnalyticCodeFilter(domain, 'fund_analytic_id', row.code);

                // Also get budget accounts for this fund
                await this._addBudgetAccountCodeFilter(domain, row.code, row.parent_activity_code);
            }
        } else if (row.type === 'account') {
            // For account rows, filter by parent analytic codes and account code
            if (row.parent_activity_code) {
                await this._addAnalyticCodeFilter(domain, 'activity_analytic_id', row.parent_activity_code);
            }
            if (row.parent_fund_code) {
                await this._addAnalyticCodeFilter(domain, 'fund_analytic_id', row.parent_fund_code);
            }
            if (row.code) {
                // Filter budget accounts by code prefix
                const accountIds = await this._getBudgetAccountsByCode(row.code);
                if (accountIds && accountIds.length > 0) {
                    domain.push(['account_id', 'in', accountIds]);
                }
            }
        }
    }

    // Get analytic IDs including children (for hierarchical filtering)
    async _getAnalyticWithChildren(analyticId, dimension) {
        try {
            const children = await this.orm.call(
                "budget.report.summary",
                "get_analytic_children",
                [analyticId, dimension]
            );
            return children;
        } catch (error) {
            console.warn("Failed to get analytic children, using single ID:", error);
            return [analyticId];
        }
    }

    // Get budget account IDs including children
    async _getBudgetAccountWithChildren(accountId) {
        try {
            const children = await this.orm.call(
                "budget.report.summary",
                "get_budget_account_children",
                [accountId]
            );
            return children;
        } catch (error) {
            console.warn("Failed to get budget account children, using single ID:", error);
            return [accountId];
        }
    }

    // Get budget account IDs for a specific activity
    async _getBudgetAccountsForActivity(activityId) {
        try {
            const accountIds = await this.orm.call(
                "budget.report.summary",
                "get_budget_accounts_for_activity",
                [activityId]
            );
            return accountIds;
        } catch (error) {
            console.warn("Failed to get budget accounts for activity:", error);
            return [];
        }
    }

    // Get budget account IDs for a specific fund and optional parent activity
    async _getBudgetAccountsForFund(fundId, parentActivityId = null) {
        try {
            const accountIds = await this.orm.call(
                "budget.report.summary",
                "get_budget_accounts_for_fund",
                [fundId, parentActivityId]
            );
            return accountIds;
        } catch (error) {
            console.warn("Failed to get budget accounts for fund:", error);
            return [];
        }
    }

    // Add analytic filter using code prefix matching
    async _addAnalyticCodeFilter(domain, field_name, code) {
        try {
            const analyticIds = await this.orm.call(
                "budget.report.summary",
                "get_analytic_ids_by_code_prefix",
                [code, field_name]
            );
            if (analyticIds && analyticIds.length > 0) {
                domain.push([field_name, 'in', analyticIds]);
            }
        } catch (error) {
            console.warn(`Failed to get analytic IDs for ${field_name} with code ${code}:`, error);
        }
    }

    // Add budget account filter using code prefix
    async _addBudgetAccountCodeFilter(domain, code, parentCode = null) {
        try {
            const accountIds = await this.orm.call(
                "budget.report.summary",
                "get_budget_account_ids_by_code_prefix",
                [code, parentCode]
            );
            if (accountIds && accountIds.length > 0) {
                domain.push(['account_id', 'in', accountIds]);
            }
        } catch (error) {
            console.warn(`Failed to get account IDs for code ${code}:`, error);
        }
    }

    // Get budget account IDs by code prefix
    async _getBudgetAccountsByCode(code) {
        try {
            const accountIds = await this.orm.call(
                "budget.report.summary",
                "get_budget_account_ids_by_code_prefix",
                [code]
            );
            return accountIds;
        } catch (error) {
            console.warn(`Failed to get budget accounts by code ${code}:`, error);
            return [];
        }
    }

    // Get department IDs including children
    async _getDepartmentWithChildren(departmentIds) {
        try {
            const results = await Promise.all(
                departmentIds.map(deptId => this._getAnalyticWithChildren(deptId, 'departments'))
            );
            return [...new Set(results.flat())];
        } catch (error) {
            return departmentIds;
        }
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
