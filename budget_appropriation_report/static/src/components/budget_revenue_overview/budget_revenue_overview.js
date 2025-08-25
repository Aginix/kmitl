/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class BudgetRevenueOverview extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-left": true,
            "bottom-right": false
        };

        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            filters: {
                fiscal_year_id: null,
                state: null,
            },
            loading: false,
            data: null,
            fiscalYear: null,
            departments: null,
            hideEmpty: true,
            filterOptions: {
                fiscal_years: [],
                state: ["draft", "review", "posted"]
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const response = await this.orm.call(
                "budget.appropriation.report.revenue.overview",
                "get_data",
                [this.state.filters]
            );

            this.state.data = response.data;
            this.state.fiscalYear = response.fiscal_year;
            this.state.departments = response.departments;
            this.state.filters = response.filters;

            const filterOptions = await this.orm.call(
                "budget.appropriation.report.revenue.overview",
                "get_filter_options",
                []
            );

            this.state.filterOptions = filterOptions;
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

    get fiscalYear() {
        return this.state.fiscalYear;
    }

    get departments() {
        return this.state.departments;
    }

    get totalBalance() {
        let sum = 0
        for (let n of Object.values(this.state.data)) {
            sum += n.total_balance
        }
        return sum
    }

    get data() {
        const accounts = Object.values(this.state.data);
        for (let account of accounts) {
            let departmentsList = this.state.departments.map((department) => {
                return {
                    ...department,
                    balance: account["department"][department.id] || 0
                }
            });
            
            // Filter departments if hideEmpty is enabled
            if (this.state.hideEmpty) {
                departmentsList = departmentsList.filter(dept => dept.balance > 0);
            }
            
            account["departments"] = departmentsList;
        }
        return accounts
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

    async onStateChange(e) {
        this.state.filters.state = e.target.value || null

        await this.onFilterChange();
    }

    async onFiscalYearChange(e) {
        const fiscalYearId = e.target.value ? Number(e.target.value) : null
        this.state.filters.fiscal_year_id = fiscalYearId;

        await this.onFilterChange();
    }

    onToggleHideEmpty() {
        this.state.hideEmpty = !this.state.hideEmpty;
    }
}

BudgetRevenueOverview.template = "budget_appropriation_report.BudgetRevenueOverview";
BudgetRevenueOverview.components = {
    ControlPanel
};

registry
    .category("actions")
    .add("budget_appropriation_revenue_overview_report", BudgetRevenueOverview);
