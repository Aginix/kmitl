/** @odoo-module **/

import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";

export class BudgetAvailabilityWidget extends Component {
    static template = "budget.BudgetAvailabilityWidget";
    static props = {
        record: Object,
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            data: null,
            error: null,
        });
        
        onWillStart(() => this.loadBudgetData());
        onWillUpdateProps((nextProps) => {
            if (this.hasAnalyticChanges(nextProps.record)) {
                this.loadBudgetData(nextProps.record);
            }
        });
    }

    hasAnalyticChanges(newRecord) {
        const oldData = this.props.record.data;
        const newData = newRecord.data;
        
        return (
            oldData.account_id !== newData.account_id ||
            oldData.activity_analytic_id !== newData.activity_analytic_id ||
            oldData.fund_analytic_id !== newData.fund_analytic_id ||
            oldData.department_analytic_id !== newData.department_analytic_id ||
            oldData.source_analytic_id !== newData.source_analytic_id
        );
    }

    async loadBudgetData(record = this.props.record) {
        this.state.loading = true;
        this.state.error = null;

        try {
            const data = record.data;
            
            // Skip if required fields are not set
            if (!data.account_id || !data.activity_analytic_id || !data.fund_analytic_id) {
                this.state.data = null;
                this.state.loading = false;
                return;
            }

            // Get budget breakdown from the controller
            const result = await this.orm.call(
                "budget.controller",
                "get_budget_breakdown",
                [{
                    account_id: data.account_id[0],
                    activity_analytic_id: data.activity_analytic_id[0],
                    department_analytic_id: data.department_analytic_id ? data.department_analytic_id[0] : false,
                    fund_analytic_id: data.fund_analytic_id[0],
                    source_analytic_id: data.source_analytic_id ? data.source_analytic_id[0] : false,
                }],
                {
                    fiscal_year_id: data.date_range_fy_id ? data.date_range_fy_id[0] : false,
                    company_id: data.company_id ? data.company_id[0] : false,
                }
            );

            this.state.data = result;
        } catch (error) {
            console.error("Error loading budget data:", error);
            this.state.error = error.message || "Failed to load budget data";
        } finally {
            this.state.loading = false;
        }
    }

    formatAmount(amount) {
        return formatMonetary(amount, { 
            digits: [false, 2],
            currencyId: this.props.record.data.currency_id?.[0],
        });
    }

    get availablePercentage() {
        if (!this.state.data) return 0;
        const { appropriated, available } = this.state.data;
        return appropriated > 0 ? (available / appropriated) * 100 : 0;
    }

    get statusClass() {
        const percentage = this.availablePercentage;
        if (percentage >= 50) return "text-success";
        if (percentage >= 20) return "text-warning";
        return "text-danger";
    }
}

export const budgetAvailabilityWidget = {
    component: BudgetAvailabilityWidget,
};

registry.category("view_widgets").add("budget_availability", budgetAvailabilityWidget);