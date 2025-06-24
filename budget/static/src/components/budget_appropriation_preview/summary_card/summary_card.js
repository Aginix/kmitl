/** @odoo-module **/

import { Component } from "@odoo/owl";

export class SummaryCard extends Component {
    
    // ---- Getters ----

    get move() {
        return this.props.move || {};
    }

    get summary() {
        return this.props.summary || {};
    }

    get currencySymbol() {
        return this.props.currencySymbol || "฿";
    }

    get totalAmount() {
        return this.move.total_amount || 0;
    }

    get stateLabel() {
        const labels = {
            draft: "ร่าง",
            review: "รอการตรวจสอบ", 
            posted: "อนุมัติแล้ว",
            cancel: "ยกเลิก"
        };
        return labels[this.move.state] || this.move.state;
    }

    get stateBadgeClass() {
        const classes = {
            draft: "badge-secondary",
            review: "badge-warning",
            posted: "badge-success", 
            cancel: "badge-danger"
        };
        return classes[this.move.state] || "badge-secondary";
    }

    get sourceAnalytic() {
        return this.move.source_analytic || null;
    }

    get departmentAnalytic() {
        return this.move.department_analytic || null;
    }

    // ---- Helper Methods ----

    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    formatDate(dateString) {
        if (!dateString) return "";
        try {
            return new Date(dateString).toLocaleDateString('th-TH', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        } catch (error) {
            return dateString;
        }
    }

    // ---- Event Handlers ----

    onCardClick() {
        if (this.props.onCardClick) {
            this.props.onCardClick(this.move);
        }
    }
}

SummaryCard.template = "budget.SummaryCard";
SummaryCard.props = {
    move: { type: Object, optional: true },
    summary: { type: Object, optional: true },
    currencySymbol: { type: String, optional: true },
    onCardClick: { type: Function, optional: true },
};