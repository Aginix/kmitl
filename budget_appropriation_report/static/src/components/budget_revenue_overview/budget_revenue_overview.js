/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class BudgetRevenueOverview extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            loading: false,
            data: null,
            fiscalYear: null,
            departments: null,
            config: {},
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
                []
            );

            this.state.data = response.data;
            this.state.fiscalYear = response.fiscal_year;
            this.state.departments = response.departments;

            const config = await this.orm.call(
                "budget.appropriation.report.revenue.overview",
                "get_config",
                []
            );

            this.state.config = config;
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add("เกิดข้อผิดพลาดในการโหลดข้อมูล: " + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    get fiscalYear() {
        return this.state.fiscalYear;
    }

    get departments() {
        return this.state.departments;
    }

    get data() {
        const accounts = Object.values(this.state.data);
        for (let account of accounts) {
            account["departments"] = this.state.departments.map((department) => {
                return {
                    ...department,
                    balance: account["department"][department.id] || 0
                }
            });
        }
        return accounts
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    }
}

BudgetRevenueOverview.template = "budget_appropriation_report.BudgetRevenueOverview";
BudgetRevenueOverview.components = {
    ControlPanel
};

registry
    .category("actions")
    .add("budget_appropriation_revenue_overview_report", BudgetRevenueOverview);
