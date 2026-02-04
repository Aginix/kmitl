/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BudgetAppropriationF4Preview extends Component {
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

            const appropriationId = this.activeId;
            if (!appropriationId) {
                console.error("Debug info - Available props:", {
                    action: this.props.action,
                    resId: this.props.resId,
                    props: Object.keys(this.props)
                });
                throw new Error("ไม่พบ Budget Appropriation ID - กรุณาเปิดหน้าตัวอย่างจากรายการงบประมาณ");
            }

            const result = await this.orm.call(
                "budget.appropriation.f4.report",
                "get_f4_data",
                [appropriationId]
            );

            if (result.error) {
                throw new Error(result.error);
            }

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

    get activeId() {
        // Try to get ID from various sources
        return this.props.action?.res_id ||
               this.props.action?.context?.active_id ||
               this.props.resId ||
               this.props.action?.params?.id;
    }

    get context() {
        return this.props.action?.context || {};
    }

    get appropriation() {
        return this.state.data.appropriation || {};
    }

    get hierarchy() {
        return this.state.data.hierarchy || [];
    }

    get totalAmount() {
        // Calculate total from hierarchy root nodes
        if (!this.state.data.hierarchy || this.state.data.hierarchy.length === 0) {
            return 0;
        }

        return this.state.data.hierarchy.reduce((total, node) => {
            return total + (node.amount_total || 0);
        }, 0);
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

    onBack() {
        // Go back to the appropriation form
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'budget.appropriation',
            res_id: this.activeId,
            views: [[false, 'form']],
            target: 'current',
        });
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
        // For F4 (revenue), we only have account hierarchy
        // Account level starts from 0 and increases for child accounts
        if (node.type === 'account') {
            const accountLevel = Math.max(0, node.level);
            const marginLeft = 16 * accountLevel;
            return `margin-left: ${marginLeft}px;`;
        }
        return '';
    }

    getNodeIcon(nodeType) {
        const icons = {
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
            account: "รหัสงบประมาณ",
            line: "รายการ"
        };
        return labels[nodeType] || "";
    }
}

BudgetAppropriationF4Preview.template = "budget_appropriation.BudgetAppropriationF4Preview";
BudgetAppropriationF4Preview.components = {
    ControlPanel
};

registry.category("actions").add("budget_appropriation_f4_preview", BudgetAppropriationF4Preview);
