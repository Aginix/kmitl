/** @odoo-module **/

import { Component } from "@odoo/owl";

export class TreeNode extends Component {
    
    // ---- Getters ----

    get node() {
        return this.props.node;
    }

    get isExpanded() {
        return this.props.isExpanded || false;
    }

    get hasChildren() {
        return this.node.children && this.node.children.length > 0;
    }

    get indentStyle() {
        const indentSize = 24; // pixels per level
        const marginLeft = (this.node.level - 1) * indentSize;
        return `margin-left: ${marginLeft}px`;
    }

    get nodeIcon() {
        const icons = {
            activity: "fa-tasks",
            department: "fa-building", 
            fund: "fa-coins",
            account: "fa-file-text",
            line: "fa-list-ul"
        };
        return icons[this.node.type] || "fa-folder";
    }

    get nodeClass() {
        const classes = [
            "budget-tree-node",
            `node-${this.node.type}`,
            `level-${this.node.level}`
        ];
        
        if (this.isExpanded) {
            classes.push("expanded");
        }
        
        if (this.hasChildren) {
            classes.push("has-children");
        }

        return classes.join(" ");
    }

    get expandIcon() {
        if (!this.hasChildren) return "";
        return this.isExpanded ? "fa-chevron-down" : "fa-chevron-right";
    }

    get badgeClass() {
        const badges = {
            activity: "badge-primary",
            department: "badge-info",
            fund: "badge-success", 
            account: "badge-warning",
            line: "badge-secondary"
        };
        return badges[this.node.type] || "badge-secondary";
    }

    get levelLabel() {
        const labels = {
            activity: "ด้าน/แผนงาน/กิจกรรม",
            department: "ส่วนงาน",
            fund: "กองทุน",
            account: "รหัสงบประมาณ",
            line: "รายการ"
        };
        return labels[this.node.type] || "";
    }

    // ---- Event Handlers ----

    onToggle() {
        if (this.hasChildren) {
            this.props.onToggle(this.node.key);
        }
    }

    onNodeClick() {
        // Handle node selection if needed
        if (this.props.onNodeClick) {
            this.props.onNodeClick(this.node);
        }
    }

    // ---- Helper Methods ----

    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    getProgressPercentage() {
        if (!this.props.totalAmount || this.props.totalAmount === 0) {
            return 0;
        }
        return Math.min(100, (this.node.total_amount / this.props.totalAmount) * 100);
    }
}

TreeNode.template = "budget.TreeNode";
TreeNode.props = {
    node: Object,
    isExpanded: { type: Boolean, optional: true },
    onToggle: Function,
    onNodeClick: { type: Function, optional: true },
    currencySymbol: { type: String, optional: true },
    totalAmount: { type: Number, optional: true },
};