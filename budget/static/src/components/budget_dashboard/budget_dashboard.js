/** @odoo-module */

import {Component, onWillStart, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";

export class BudgetDashboard extends Component {
    static template = "budget.BudgetDashboard";

    setup() {
        this.orm = useService("orm");

        this.state = useState({
            loading: false,
            filters: {
                fiscal_year_id: null,
            },
            filterOptions: {
                fiscal_years: [],
            },
            stats: {
                total_appropriation: 0,
                total_balance: 0,
            },
        });

        onWillStart(async () => {
            await this.loadFilterOptions();
            await this.loadData();
        });
    }

    async loadFilterOptions() {
        try {
            const options = await this.orm.call(
                "budget.dashboard",
                "get_filter_options",
                []
            );
            this.state.filterOptions = options;

            // Set default fiscal year to first one if available
            if (options.fiscal_years.length > 0) {
                this.state.filters.fiscal_year_id = options.fiscal_years[0].id;
            }
        } catch (error) {
            console.error("Error loading filter options:", error);
        }
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "budget.dashboard",
                "get_dashboard_data",
                [this.state.filters]
            );
            this.state.stats = data;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async onFiscalYearChange(ev) {
        const value = ev.target.value;
        this.state.filters.fiscal_year_id = value ? parseInt(value) : null;
        await this.loadData();
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(amount);
    }

    get selectedFiscalYearName() {
        if (!this.state.filters.fiscal_year_id) {
            return "ทุกปีงบประมาณ";
        }
        const fy = this.state.filterOptions.fiscal_years.find(
            (f) => f.id === this.state.filters.fiscal_year_id
        );
        return fy ? fy.name : "ทุกปีงบประมาณ";
    }
}

registry.category("actions").add("budget_dashboard", BudgetDashboard);
