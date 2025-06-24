/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { SummaryCard } from "./summary_card/summary_card";

export class BudgetAppropriationPreview extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-right": false,
            "bottom-right": false,
        };

        this.state = useState({
            data: {},
            loading: true,
            error: null,
            expandedNodes: new Set(),
            searchTerm: "",
            filterLevel: "all",
            hideDepartment: false,
        });

        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        try {
            this.state.loading = true;
            this.state.error = null;
            
            const moveId = this.activeId;
            if (!moveId) {
                throw new Error("ไม่พบ Budget Move ID");
            }

            const result = await this.orm.call(
                "budget.appropriation.report",
                "get_hierarchical_data",
                [moveId, { hide_department: this.state.hideDepartment }]
            );

            if (result.error) {
                throw new Error(result.error);
            }

            this.state.data = result;
            
            // Auto-expand first level by default
            if (result.hierarchy && result.hierarchy.length > 0) {
                result.hierarchy.forEach(node => {
                    this.state.expandedNodes.add(node.key);
                });
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

    get activeId() {
        return this.props.action?.context?.active_id || this.props.resId;
    }

    get context() {
        return this.props.action?.context || {};
    }

    get move() {
        return this.state.data.move || {};
    }

    get hierarchy() {
        if (!this.state.data.hierarchy) return [];
        
        // Apply search filter
        if (this.state.searchTerm) {
            return this.filterHierarchy(this.state.data.hierarchy, this.state.searchTerm);
        }
        
        return this.state.data.hierarchy;
    }

    get summary() {
        return this.state.data.summary || {};
    }

    get totalAmount() {
        return this.move.total_amount || 0;
    }

    get currencySymbol() {
        return this.move.currency_symbol || "฿";
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

    onSearch(event) {
        this.state.searchTerm = event.target.value.toLowerCase();
    }

    onFilterLevel(level) {
        this.state.filterLevel = level;
    }

    onToggleDepartment() {
        this.state.hideDepartment = !this.state.hideDepartment;
        this.loadData(); // Reload data with new setting
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

    onExport() {
        // Export to PDF using the QWeb report
        const moveId = this.activeId;
        if (!moveId) {
            this.notification.add("ไม่พบข้อมูลเอกสาร", { type: "danger" });
            return;
        }
        
        // Trigger the PDF report action
        this.actionService.doAction({
            type: 'ir.actions.report',
            report_type: 'qweb-pdf',
            report_name: 'budget.report_budget_appropriation',
            report_file: 'budget.report_budget_appropriation',
            data: null,
            context: {
                active_ids: [moveId],
                active_id: moveId,
                active_model: 'budget.move',
            },
        });
    }

    onRefresh() {
        this.loadData();
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

    filterHierarchy(nodes, searchTerm) {
        const filtered = [];
        
        for (const node of nodes) {
            const matchesSearch = 
                node.name.toLowerCase().includes(searchTerm) ||
                node.code.toLowerCase().includes(searchTerm);
            
            let filteredChildren = [];
            if (node.children && node.children.length > 0) {
                filteredChildren = this.filterHierarchy(node.children, searchTerm);
            }
            
            if (matchesSearch || filteredChildren.length > 0) {
                filtered.push({
                    ...node,
                    children: filteredChildren
                });
                
                // Auto-expand matched nodes
                this.state.expandedNodes.add(node.key);
            }
        }
        
        return filtered;
    }

    isNodeExpanded(nodeKey) {
        return this.state.expandedNodes.has(nodeKey);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    getNodeIcon(nodeType) {
        const icons = {
            activity: "fa-tasks",
            department: "fa-building",
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
            activity: "ด้าน/แผนงาน/กิจกรรม",
            department: "ส่วนงาน",
            fund: "กองทุน",
            account: "รหัสงบประมาณ",
            line: "รายการ"
        };
        return labels[nodeType] || "";
    }
}

BudgetAppropriationPreview.template = "budget.BudgetAppropriationPreview";
BudgetAppropriationPreview.components = { 
    ControlPanel, 
    SummaryCard 
};

registry.category("actions").add("budget_appropriation_preview", BudgetAppropriationPreview);