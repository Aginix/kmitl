/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class BudgetExecutionReportInteractive extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        
        // State Management
        this.state = useState({
            // Loading States
            loading: true,
            error: null,
            
            // Filter State
            filters: {
                date_from: null,
                date_to: null,
                fiscal_year_id: null,
                activity_analytic_ids: [],
                fund_analytic_ids: [],
                budget_account_ids: [],
                budget_type: 'expense'
            },
            
            // Filter Options
            filterOptions: {
                fiscal_years: [],
                activities: [],
                departments: [],
                funds: [],
                sources: [],
                budget_accounts: []
            },
            
            // Data State
            rawHierarchicalData: [],      // Original from backend
            flattenedData: [],            // Processed flat list
            displayData: [],              // Filtered for display
            
            // UI State
            expandedNodes: new Set(),
            searchTerm: '',
            sortBy: 'name',
            sortDesc: false,
            
            // Summary
            totals: {
                initial_appropriation: 0,
                current_budget: 0,
                reserved_amount: 0,
                obligated_amount: 0,
                disbursed_amount: 0,
                total_used: 0,
                remaining_budget: 0,
                utilization: 0
            }
        });
        
        onWillStart(async () => {
            await this.loadFilterOptions();
            await this.setDefaultFilters();
            await this.loadData();
        });
    }
    
    // Data Loading Methods
    async loadFilterOptions() {
        try {
            const options = await this.orm.call(
                "budget.execution.status.report",
                "get_filter_options",
                []
            );
            this.state.filterOptions = options;
        } catch (error) {
            console.error("Error loading filter options:", error);
            this.state.error = "ไม่สามารถโหลดตัวเลือกการกรองได้";
        }
    }
    
    async setDefaultFilters() {
        // Set default fiscal year if available
        if (this.state.filterOptions?.fiscal_years?.length > 0) {
            const currentFY = this.state.filterOptions.fiscal_years.find(fy => fy.is_current) 
                || this.state.filterOptions.fiscal_years[0];
            
            if (currentFY) {
                this.state.filters.fiscal_year_id = currentFY.id;
                this.state.filters.date_from = currentFY.date_start;
                this.state.filters.date_to = currentFY.date_end;
            }
        }
        
        // If no dates set, use current year as fallback
        if (!this.state.filters.date_from || !this.state.filters.date_to) {
            const today = new Date();
            const year = today.getFullYear();
            this.state.filters.date_from = `${year}-01-01`;
            this.state.filters.date_to = `${year}-12-31`;
        }
    }
    
    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        
        try {
            const result = await this.orm.call(
                "budget.execution.status.report",
                "get_interactive_report_data",
                [this.state.filters]
            );
            
            // Store raw data
            this.state.rawHierarchicalData = result.hierarchical_data || [];
            
            // Process into flattened structure
            this.state.flattenedData = this.preprocessHierarchicalData(this.state.rawHierarchicalData);
            
            // Update visibility and display
            this.updateVisibility();
            
            // Calculate totals
            this.calculateTotals();
            
        } catch (error) {
            console.error("Error loading report data:", error);
            this.state.error = "เกิดข้อผิดพลาดในการโหลดข้อมูลรายงาน";
        } finally {
            this.state.loading = false;
        }
    }
    
    // Data Processing Methods
    preprocessHierarchicalData(hierarchicalData) {
        const flatList = [];
        const nodeMap = new Map();
        
        // First pass: Flatten and create node map
        const processNode = (node, parentKey = null, level = 0) => {
            const flatNode = {
                // Copy all node data
                ...node,
                
                // Add hierarchy metadata
                parentKey,
                level,
                childKeys: [],
                hasChildren: node.children && node.children.length > 0,
                childCount: node.children ? node.children.length : 0,
                
                // Calculate display properties
                displayName: this.getDisplayName(node),
                statusClass: this.getStatusClass(node),
                rowClass: this.getRowClass(node),
                
                // Initial UI state
                isVisible: level === 0, // Only root nodes visible initially
                isExpanded: false,
                isHighlighted: false
            };
            
            // Store in flat list and map
            flatList.push(flatNode);
            nodeMap.set(node.key, flatNode);
            
            // Process children
            if (node.children) {
                node.children.forEach(child => {
                    flatNode.childKeys.push(child.key);
                    processNode(child, node.key, level + 1);
                });
            }
            
            // Remove children from flat node to avoid duplication
            delete flatNode.children;
        };
        
        // Process all root nodes
        hierarchicalData.forEach(root => processNode(root));
        
        // Second pass: Update parent references and paths
        flatList.forEach(node => {
            if (node.parentKey && nodeMap.has(node.parentKey)) {
                const parent = nodeMap.get(node.parentKey);
                node.fullPath = parent.fullPath ? parent.fullPath + ' > ' + node.name : node.name;
            } else {
                node.fullPath = node.name;
            }
        });
        
        return flatList;
    }
    
    // Visibility Management
    updateVisibility() {
        const expandedSet = this.state.expandedNodes;
        
        this.state.flattenedData.forEach(node => {
            if (!node.parentKey) {
                // Root nodes always visible
                node.isVisible = true;
            } else {
                // Check if all ancestors are expanded
                node.isVisible = this.areAllAncestorsExpanded(node);
            }
        });
        
        // Update display data
        this.updateDisplayData();
    }
    
    areAllAncestorsExpanded(node) {
        let current = node;
        while (current.parentKey) {
            if (!this.state.expandedNodes.has(current.parentKey)) {
                return false;
            }
            // Find parent node
            current = this.state.flattenedData.find(n => n.key === current.parentKey);
            if (!current) return false;
        }
        return true;
    }
    
    // Display Data Management
    updateDisplayData() {
        // Filter visible nodes
        let displayData = this.state.flattenedData.filter(node => node.isVisible);
        
        // Apply search filter
        if (this.state.searchTerm) {
            displayData = this.filterBySearch(displayData);
        }
        
        // Update state
        this.state.displayData = displayData;
    }
    
    filterBySearch(data) {
        const searchTerm = this.state.searchTerm.toLowerCase();
        return data.filter(node => {
            return node.name.toLowerCase().includes(searchTerm) ||
                   (node.code && node.code.toLowerCase().includes(searchTerm));
        });
    }
    
    // Calculate Totals
    calculateTotals() {
        const totals = {
            initial_appropriation: 0,
            current_budget: 0,
            reserved_amount: 0,
            obligated_amount: 0,
            disbursed_amount: 0,
            total_used: 0,
            remaining_budget: 0
        };
        
        // Sum only root level nodes to avoid double counting
        this.state.flattenedData.forEach(node => {
            if (!node.parentKey && node.totals) {
                Object.keys(totals).forEach(key => {
                    totals[key] += node.totals[key] || 0;
                });
            }
        });
        
        // Calculate utilization
        if (totals.current_budget > 0) {
            totals.utilization = (totals.total_used / totals.current_budget) * 100;
        } else {
            totals.utilization = 0;
        }
        
        this.state.totals = totals;
    }
    
    // Event Handlers
    toggleNode(nodeKey) {
        if (this.state.expandedNodes.has(nodeKey)) {
            this.state.expandedNodes.delete(nodeKey);
        } else {
            this.state.expandedNodes.add(nodeKey);
        }
        this.updateVisibility();
    }
    
    expandAll() {
        this.state.flattenedData.forEach(node => {
            if (node.hasChildren) {
                this.state.expandedNodes.add(node.key);
            }
        });
        this.updateVisibility();
    }
    
    collapseAll() {
        this.state.expandedNodes.clear();
        this.updateVisibility();
    }
    
    async onRefresh() {
        await this.loadData();
        this.notification.add("รีเฟรชข้อมูลเรียบร้อยแล้ว", { type: "success" });
    }
    
    async onExport() {
        try {
            this.state.loading = true;
            
            const result = await this.orm.call(
                "budget.execution.status.report",
                "export_to_excel",
                [this.state.filters]
            );
            
            if (result && result.url) {
                window.location.href = result.url;
                this.notification.add("ส่งออกข้อมูลเรียบร้อยแล้ว", { type: "success" });
            }
        } catch (error) {
            console.error("Error exporting to Excel:", error);
            this.notification.add("เกิดข้อผิดพลาดในการส่งออกข้อมูล", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }
    
    async onPrint() {
        try {
            await this.actionService.doAction({
                type: "ir.actions.report",
                report_type: "qweb-pdf",
                report_name: "budget.budget_execution_status_report_document",
                data: {
                    filters: this.state.filters
                },
                context: this.env.context
            });
        } catch (error) {
            console.error("Error printing report:", error);
            this.notification.add("เกิดข้อผิดพลาดในการพิมพ์รายงาน", { type: "danger" });
        }
    }
    
    onSearch(event) {
        this.state.searchTerm = event.target.value;
        this.updateDisplayData();
    }
    
    // Utility Methods
    getDisplayName(node) {
        return node.code ? `${node.code} - ${node.name}` : node.name;
    }
    
    getStatusClass(node) {
        const util = node.utilization || 0;
        if (util > 100) return 'danger';
        if (util > 90) return 'warning';
        if (util < 25) return 'info';
        return 'normal';
    }
    
    getRowClass(node) {
        const classes = [];
        
        // Type-based class
        classes.push(`hierarchy-row`);
        classes.push(node.type);
        
        // Status-based class
        if (node.totals && node.totals.remaining_budget < 0) {
            classes.push('table-danger');
        } else if (node.utilization > 90) {
            classes.push('table-warning');
        }
        
        return classes.join(' ');
    }
    
    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    }
    
    formatPercentage(value) {
        return `${(value || 0).toFixed(2)}%`;
    }
}

BudgetExecutionReportInteractive.template = "budget.BudgetExecutionReportInteractive";

registry.category("actions").add("budget_execution_report_interactive", BudgetExecutionReportInteractive);