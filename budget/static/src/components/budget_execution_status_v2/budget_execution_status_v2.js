/** @odoo-module */

import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class BudgetExecutionStatusV2 extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.user = useService("user");
        this.rpc = useService("rpc");
        
        // Refs for DOM elements
        this.tableContainerRef = useRef("tableContainer");
        
        // Component state
        this.state = useState({
            // Loading states
            isLoading: true,
            isRefreshing: false,
            error: null,
            
            // Data
            reportData: null,
            hierarchicalData: [],
            flatData: [],
            displayData: [],
            
            // Filters 
            filters: {
                date_from: null,
                date_to: null,
                date_range_fy_id: null,
                budget_type: 'expense',
                activity_analytic_ids: [],
                department_analytic_ids: [],
                fund_analytic_ids: [],
                source_analytic_ids: [],
                budget_account_ids: [],
            },
            
            // Filter options
            filterOptions: {
                fiscal_years: [],
                activities: [],
                departments: [],
                funds: [],
                sources: [],
                budget_accounts: []
            },
            
            // UI state
            expandedNodes: new Set(),
            selectedNodes: new Set(),
            searchTerm: '',
            sortConfig: {
                field: null,
                direction: 'asc'
            },
            
            // View options
            viewMode: 'hierarchical', // 'hierarchical' or 'flat'
            showZeroValues: false,
            showPercentages: true,
            
            // Real-time updates
            autoRefresh: false,
            refreshInterval: 30000, // 30 seconds
            lastRefreshTime: null,
            
            // Summary
            summary: {
                total_initial_appropriation: 0,
                total_current_budget: 0,
                total_requested: 0,
                total_reserved: 0,
                total_obligated: 0,
                total_disbursed: 0,
                total_used: 0,
                total_remaining: 0,
                total_returned: 0,
                utilization_percentage: 0,
            },
            
            // Pagination
            currentPage: 1,
            pageSize: 100,
            totalRecords: 0,
            
            // Filter panel visibility
            showFilterPanel: false,
        });
        
        // Auto-refresh timer
        this.refreshTimer = null;
        
        onWillStart(async () => {
            await this.loadInitialData();
        });
        
        onMounted(() => {
            this.setupKeyboardShortcuts();
            this.setupAutoRefresh();
        });
    }
    
    // Lifecycle methods
    willUnmount() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
    }
    
    // Data loading methods
    async loadInitialData() {
        try {
            this.state.isLoading = true;
            this.state.error = null;
            
            // Load filter options
            await this.loadFilterOptions();
            
            // Set default filters
            await this.setDefaultFilters();
            
            // Load report data
            await this.loadReportData();
            
        } catch (error) {
            console.error("Error loading initial data:", error);
            this.state.error = "Failed to load report data. Please try again.";
        } finally {
            this.state.isLoading = false;
        }
    }
    
    async loadFilterOptions() {
        const options = await this.orm.call(
            "budget.execution.status.report",
            "get_filter_options",
            []
        );
        
        // Update state with options
        this.state.filterOptions = options;
        
        // Set default fiscal year
        if (options.fiscal_years && options.fiscal_years.length > 0) {
            const currentFY = options.fiscal_years.find(fy => fy.is_current);
            if (currentFY) {
                this.state.filters.date_range_fy_id = currentFY.id;
                this.state.filters.date_from = currentFY.date_start;
                this.state.filters.date_to = currentFY.date_end;
            }
        }
    }
    
    async setDefaultFilters() {
        // Get user preferences from local storage
        const savedFilters = localStorage.getItem('budget_execution_filters');
        if (savedFilters) {
            try {
                const parsed = JSON.parse(savedFilters);
                Object.assign(this.state.filters, parsed);
            } catch (e) {
                console.error("Error parsing saved filters:", e);
            }
        }
        
        // Ensure we have valid dates
        if (!this.state.filters.date_from || !this.state.filters.date_to) {
            const today = new Date();
            const year = today.getFullYear();
            this.state.filters.date_from = `${year}-01-01`;
            this.state.filters.date_to = `${year}-12-31`;
        }
    }
    
    async loadReportData() {
        try {
            this.state.isRefreshing = true;
            
            const result = await this.orm.call(
                "budget.execution.status.report",
                "get_interactive_report_data",
                [this.state.filters]
            );
            
            // Update state with new data
            this.state.reportData = result;
            this.state.hierarchicalData = result.hierarchical_data || [];
            this.state.summary = result.summary || this.getEmptySummary();
            
            // Process data
            this.processReportData();
            
            // Update last refresh time
            this.state.lastRefreshTime = new Date();
            
            // Save filters to local storage
            localStorage.setItem('budget_execution_filters', JSON.stringify(this.state.filters));
            
        } catch (error) {
            console.error("Error loading report data:", error);
            throw error;
        } finally {
            this.state.isRefreshing = false;
        }
    }
    
    // Data processing methods
    processReportData() {
        // Flatten hierarchical data for easier manipulation
        this.state.flatData = this.flattenHierarchicalData(this.state.hierarchicalData);
        
        // Apply initial visibility based on expanded nodes
        this.updateNodeVisibility();
        
        // Apply filters and sorting
        this.updateDisplayData();
        
        // Update pagination
        this.updatePagination();
    }
    
    flattenHierarchicalData(nodes, parentKey = null, level = 0) {
        const result = [];
        
        for (const node of nodes) {
            const flatNode = {
                ...node,
                _parentKey: parentKey,
                _level: level,
                _hasChildren: node.children && node.children.length > 0,
                _isExpanded: this.state.expandedNodes.has(node.key),
                _isVisible: level === 0 || this.isNodeVisible(node.key),
                _isSelected: this.state.selectedNodes.has(node.key),
            };
            
            result.push(flatNode);
            
            if (node.children && node.children.length > 0) {
                result.push(...this.flattenHierarchicalData(node.children, node.key, level + 1));
            }
        }
        
        return result;
    }
    
    updateNodeVisibility() {
        for (const node of this.state.flatData) {
            if (node._level === 0) {
                node._isVisible = true;
            } else {
                node._isVisible = this.isNodeVisible(node.key);
            }
        }
    }
    
    isNodeVisible(nodeKey) {
        const node = this.state.flatData.find(n => n.key === nodeKey);
        if (!node || !node._parentKey) return true;
        
        const parent = this.state.flatData.find(n => n.key === node._parentKey);
        if (!parent) return true;
        
        return parent._isExpanded && this.isNodeVisible(parent.key);
    }
    
    updateDisplayData() {
        let displayData = [...this.state.flatData];
        
        // Filter by visibility
        if (this.state.viewMode === 'hierarchical') {
            displayData = displayData.filter(node => node._isVisible);
        }
        
        // Filter by search term
        if (this.state.searchTerm) {
            displayData = this.filterBySearch(displayData);
        }
        
        // Filter zero values
        if (!this.state.showZeroValues) {
            displayData = displayData.filter(node => 
                node.totals && node.totals.current_budget > 0
            );
        }
        
        // Apply sorting
        if (this.state.sortConfig.field) {
            displayData = this.sortData(displayData);
        }
        
        this.state.displayData = displayData;
        this.state.totalRecords = displayData.length;
    }
    
    filterBySearch(data) {
        const searchTerm = this.state.searchTerm.toLowerCase();
        const matchedNodes = new Set();
        
        // Find all matching nodes and their ancestors
        for (const node of data) {
            if (node.name.toLowerCase().includes(searchTerm) ||
                (node.code && node.code.toLowerCase().includes(searchTerm))) {
                // Add this node and all its ancestors
                matchedNodes.add(node.key);
                let parent = data.find(n => n.key === node._parentKey);
                while (parent) {
                    matchedNodes.add(parent.key);
                    parent = data.find(n => n.key === parent._parentKey);
                }
            }
        }
        
        return data.filter(node => matchedNodes.has(node.key));
    }
    
    sortData(data) {
        const { field, direction } = this.state.sortConfig;
        const multiplier = direction === 'asc' ? 1 : -1;
        
        return data.sort((a, b) => {
            let aVal = a.totals?.[field] || 0;
            let bVal = b.totals?.[field] || 0;
            
            if (field === 'name' || field === 'code') {
                aVal = a[field] || '';
                bVal = b[field] || '';
                return aVal.localeCompare(bVal) * multiplier;
            }
            
            return (aVal - bVal) * multiplier;
        });
    }
    
    updatePagination() {
        const startIdx = (this.state.currentPage - 1) * this.state.pageSize;
        const endIdx = startIdx + this.state.pageSize;
        this.state.displayData = this.state.displayData.slice(startIdx, endIdx);
    }
    
    // Filter handling
    toggleFilterPanel() {
        this.state.showFilterPanel = !this.state.showFilterPanel;
    }
    
    async onFilterChange() {
        await this.loadReportData();
    }
    
    onFiscalYearChange(event) {
        const fyId = parseInt(event.target.value);
        if (fyId) {
            const fy = this.state.filterOptions.fiscal_years.find(f => f.id === fyId);
            if (fy) {
                this.state.filters.date_range_fy_id = fyId;
                this.state.filters.date_from = fy.date_start;
                this.state.filters.date_to = fy.date_end;
                this.onFilterChange();
            }
        }
    }
    
    // UI Event Handlers
    async onRefresh() {
        await this.loadReportData();
        this.notification.add("Report refreshed successfully", { 
            type: "success",
            title: "Success"
        });
    }
    
    toggleNode(nodeKey) {
        if (this.state.expandedNodes.has(nodeKey)) {
            this.state.expandedNodes.delete(nodeKey);
        } else {
            this.state.expandedNodes.add(nodeKey);
        }
        
        // Reprocess data to update visibility
        this.processReportData();
    }
    
    expandAll() {
        for (const node of this.state.flatData) {
            if (node._hasChildren) {
                this.state.expandedNodes.add(node.key);
            }
        }
        this.processReportData();
    }
    
    collapseAll() {
        this.state.expandedNodes.clear();
        this.processReportData();
    }
    
    toggleViewMode() {
        this.state.viewMode = this.state.viewMode === 'hierarchical' ? 'flat' : 'hierarchical';
        this.updateDisplayData();
    }
    
    toggleZeroValues() {
        this.state.showZeroValues = !this.state.showZeroValues;
        this.updateDisplayData();
    }
    
    toggleAutoRefresh() {
        this.state.autoRefresh = !this.state.autoRefresh;
        this.setupAutoRefresh();
        
        if (this.state.autoRefresh) {
            this.notification.add("Auto-refresh enabled (30s)", { type: "info" });
        } else {
            this.notification.add("Auto-refresh disabled", { type: "info" });
        }
    }
    
    setupAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
        
        if (this.state.autoRefresh) {
            this.refreshTimer = setInterval(() => {
                this.loadReportData();
            }, this.state.refreshInterval);
        }
    }
    
    onSort(field) {
        if (this.state.sortConfig.field === field) {
            // Toggle direction
            this.state.sortConfig.direction = 
                this.state.sortConfig.direction === 'asc' ? 'desc' : 'asc';
        } else {
            // New field
            this.state.sortConfig.field = field;
            this.state.sortConfig.direction = 'asc';
        }
        
        this.updateDisplayData();
    }
    
    onSearch(event) {
        this.state.searchTerm = event.target.value;
        this.updateDisplayData();
    }
    
    onPageChange(page) {
        this.state.currentPage = page;
        this.updatePagination();
    }
    
    // Export functionality
    async onExportExcel() {
        try {
            const response = await this.rpc("/budget/execution_status/export/excel", {
                filters: this.state.filters,
                include_details: true,
            });
            
            if (response.url) {
                window.location.href = response.url;
                this.notification.add("Excel export started", { type: "success" });
            }
        } catch (error) {
            console.error("Export error:", error);
            this.notification.add("Export failed", { type: "danger" });
        }
    }
    
    async onPrint() {
        await this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: "budget.budget_execution_status_report_document",
            data: {
                filters: this.state.filters,
                summary: this.state.summary,
            },
            context: this.env.context,
        });
    }
    
    // Keyboard shortcuts
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', this.handleKeyboard.bind(this));
    }
    
    handleKeyboard(event) {
        // Ctrl/Cmd + R: Refresh
        if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
            event.preventDefault();
            this.onRefresh();
        }
        
        // Ctrl/Cmd + E: Export
        if ((event.ctrlKey || event.metaKey) && event.key === 'e') {
            event.preventDefault();
            this.onExportExcel();
        }
        
        // Ctrl/Cmd + P: Print
        if ((event.ctrlKey || event.metaKey) && event.key === 'p') {
            event.preventDefault();
            this.onPrint();
        }
    }
    
    // Utility methods
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
    
    formatDate(date) {
        if (!date) return '';
        return new Date(date).toLocaleDateString('th-TH');
    }
    
    getStatusClass(node) {
        if (!node.totals) return '';
        
        const utilization = node.utilization || 0;
        if (node.totals.remaining_budget < 0) return 'danger';
        if (utilization > 90) return 'warning';
        if (utilization < 25) return 'info';
        return 'success';
    }
    
    getEmptySummary() {
        return {
            total_initial_appropriation: 0,
            total_current_budget: 0,
            total_requested: 0,
            total_reserved: 0,
            total_obligated: 0,
            total_disbursed: 0,
            total_used: 0,
            total_remaining: 0,
            total_returned: 0,
            utilization_percentage: 0,
        };
    }
}

BudgetExecutionStatusV2.template = "budget.BudgetExecutionStatusV2";
BudgetExecutionStatusV2.props = {};

// Register the component
registry.category("actions").add("budget_execution_status_v2", BudgetExecutionStatusV2);