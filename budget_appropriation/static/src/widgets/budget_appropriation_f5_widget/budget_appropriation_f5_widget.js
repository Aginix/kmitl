/** @odoo-module **/

import { Component, onWillStart, useState, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BudgetAppropriationF5Widget extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        this.state = useState({
            data: {},
            loading: true,
            error: null,
            expandedNodes: new Set(),
            searchTerm: "",
        });

        onWillStart(async () => {
            await this.loadF5Data();
        });

        onWillUpdateProps(async (nextProps) => {
            // Reload data when record changes
            if (nextProps.record.resId !== this.props.record.resId) {
                await this.loadF5Data();
            }
        });
    }

    async loadF5Data() {
        try {
            this.state.loading = true;
            this.state.error = null;
            
            const appropriationId = this.props.record.resId;
            if (!appropriationId) {
                this.state.error = "ไม่พบข้อมูลการจัดสรรงบประมาณ";
                return;
            }

            const result = await this.orm.call(
                "budget.appropriation.f5.report",
                "get_f5_data",
                [appropriationId]
            );

            if (result.error) {
                this.state.error = result.error;
                return;
            }

            this.state.data = result;
            
            // Auto-expand all nodes by default
            if (result.hierarchy && result.hierarchy.length > 0) {
                const allKeys = this.getAllNodeKeys(result.hierarchy);
                allKeys.forEach(key => this.state.expandedNodes.add(key));
            }

        } catch (error) {
            console.error("Error loading F5 data:", error);
            this.state.error = "เกิดข้อผิดพลาดในการโหลดข้อมูล F5";
            this.notification.add("เกิดข้อผิดพลาดในการโหลดข้อมูล F5", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    getAllNodeKeys(nodes) {
        let keys = [];
        for (const node of nodes) {
            keys.push(node.id);
            if (node.children && node.children.length > 0) {
                keys = keys.concat(this.getAllNodeKeys(node.children));
            }
        }
        return keys;
    }

    toggleNode(nodeId) {
        if (this.state.expandedNodes.has(nodeId)) {
            this.state.expandedNodes.delete(nodeId);
        } else {
            this.state.expandedNodes.add(nodeId);
        }
    }

    isExpanded(nodeId) {
        return this.state.expandedNodes.has(nodeId);
    }

    formatCurrency(amount) {
        const currencySymbol = this.state.data.appropriation?.currency_symbol || "฿";
        return `${currencySymbol} ${Number(amount).toLocaleString('th-TH', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })}`;
    }

    // Search functionality
    get filteredHierarchy() {
        if (!this.state.searchTerm || !this.state.data.hierarchy) {
            return this.state.data.hierarchy || [];
        }
        return this.filterHierarchy(this.state.data.hierarchy, this.state.searchTerm.toLowerCase());
    }

    filterHierarchy(nodes, searchTerm) {
        const filtered = [];
        for (const node of nodes) {
            const nodeMatches = 
                node.name?.toLowerCase().includes(searchTerm) ||
                node.code?.toLowerCase().includes(searchTerm);
            
            let filteredChildren = [];
            if (node.children) {
                filteredChildren = this.filterHierarchy(node.children, searchTerm);
            }
            
            if (nodeMatches || filteredChildren.length > 0) {
                filtered.push({
                    ...node,
                    children: filteredChildren
                });
            }
        }
        return filtered;
    }

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
    }

    clearSearch() {
        this.state.searchTerm = "";
    }

    expandAll() {
        if (this.state.data.hierarchy) {
            const allKeys = this.getAllNodeKeys(this.state.data.hierarchy);
            allKeys.forEach(key => this.state.expandedNodes.add(key));
        }
    }

    collapseAll() {
        this.state.expandedNodes.clear();
    }

    // Getters for template
    get appropriation() {
        return this.state.data.appropriation || {};
    }

    get summary() {
        return this.state.data.summary || {};
    }

    get hasData() {
        return this.state.data.hierarchy && this.state.data.hierarchy.length > 0;
    }
}

BudgetAppropriationF5Widget.template = "budget_appropriation.F5Widget";

registry.category("view_widgets").add("budget_appropriation_f5_widget", BudgetAppropriationF5Widget);